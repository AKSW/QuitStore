import traceback
import re

import logging
from werkzeug.http import parse_accept_header, parse_options_header
from flask import Blueprint, request, current_app, make_response, Markup
from rdflib import ConjunctiveGraph
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate
from rdflib.plugins.sparql.algebra import translateQuery, translateUpdate
from quit.conf import Feature
from quit.web.app import render_template, feature_required
from quit.exceptions import UnSupportedQueryType

logger = logging.getLogger('quit.modules.endpoint')

__all__ = ('endpoint')

endpoint = Blueprint('endpoint', __name__)

# querytype: { accept type: [content type, serializer_format]}
resultSetMimetypes = {
    '*/*': ['application/sparql-results+xml', 'xml'],
    'application/sparql-results+xml': ['application/sparql-results+xml', 'xml'],
    'application/xml': ['application/xml', 'xml'],
    'application/rdf+xml': ['application/rdf+xml', 'xml'],
    'application/json': ['application/json', 'json'],
    'application/sparql-results+json': ['application/sparql-results+json', 'json'],
    'text/csv': ['text/csv', 'csv'],
    'text/html': ['text/html', 'html'],
    'application/xhtml+xml': ['application/xhtml+xml', 'html']
}
rdfMimetypes = {
    '*/*': ['text/turtle', 'turtle'],
    'text/turtle': ['text/turtle', 'turtle'],
    'application/x-turtle': ['application/x-turtle', 'turtle'],
    'application/rdf+xml': ['application/rdf+xml', 'xml'],
    'application/xml': ['application/xml', 'xml'],
    'application/n-triples': ['application/n-triples', 'nt11'],
    'application/trig': ['application/trig', 'trig']
}


def parse_query_type(query):
    try:
        translatedQuery = translateQuery(parseQuery(query), {}, None)
        return translatedQuery.algebra.name, translatedQuery
    except Exception:
        pass

    try:
        parsetree = parseUpdate(query)
        translatedUpdate = translateUpdate(parsetree, {}, None)
        return parsetree.request[0].name, translatedUpdate
    except Exception:
        raise UnSupportedQueryType


@endpoint.route("/sparql", defaults={'branch_or_ref': None}, methods=['POST', 'GET'])
@endpoint.route("/sparql/<path:branch_or_ref>", methods=['POST', 'GET'])
def sparql(branch_or_ref):
    """Process a SPARQL query (Select or Update).

    Returns:
        HTTP Response with query result: If query was a valid select query.
        HTTP Response 200: If request contained a valid update query.
        HTTP Response 406: If accept header is not acceptable.
    """
    quit = current_app.config['quit']
    default_branch = quit.config.getDefaultBranch()

    if not branch_or_ref and not quit.repository.is_empty:
        branch_or_ref = default_branch

    logger.debug("Request method: {}".format(request.method))

    query = None
    if request.method == "GET":
        default_graph = request.args.get('default-graph-uri', None)
        named_graph = request.args.get('named-graph-uri', None)
        query = request.args.get('query', None)
    elif request.method == "POST":
        if 'Content-Type' in request.headers:
            contentMimeType, options = parse_options_header(request.headers['Content-Type'])
            if contentMimeType == "application/x-www-form-urlencoded":
                if 'query' in request.form:
                    default_graph = request.form.get('default-graph-uri', None)
                    named_graph = request.form.get('named-graph-uri', None)
                    query = request.form.get('query', None)
                elif 'update' in request.form:
                    default_graph = request.form.get('using-graph-uri', None)
                    named_graph = request.form.get('using-named-graph-uri', None)
                    query = request.form.get('update', None)
            elif contentMimeType == "application/sparql-query":
                default_graph = request.args.get('default-graph-uri', None)
                named_graph = request.args.get('named-graph-uri', None)
                query = request.data.decode("utf-8")
            elif contentMimeType == "application/sparql-update":
                default_graph = request.args.get('using-graph-uri', None)
                named_graph = request.args.get('using-named-graph-uri', None)
                query = request.data.decode("utf-8")

    if 'Accept' in request.headers:
        logger.info('Received query via {}: {} with accept header: {}'.format(
            request.method, query, request.headers['Accept']))
        mimetype = parse_accept_header(request.headers['Accept']).best
    else:
        logger.info('Received query via {}: {} with no accept header.'.format(request.method,
                                                                              query))
        mimetype = '*/*'

    if query is None:
        if mimetype == 'text/html':
            return render_template('sparql.html', current_ref=branch_or_ref)
        else:
            return make_response('No Query was specified or the Content-Type is not set according' +
                                 'to the SPARQL 1.1 standard', 400)

    try:
        queryType, parsedQuery = parse_query_type(query)
        graph = quit.instance(branch_or_ref)
    except UnSupportedQueryType as e:
        logger.exception(e)
        return make_response('Unsupported Query Type', 400)
    except Exception as e:
        logger.exception(e)
        return make_response('No branch or reference given.', 400)

    if queryType in ['InsertData', 'DeleteData', 'Modify']:
        res = graph.update(parsedQuery)

        try:
            ref = request.values.get('ref', None) or default_branch
            ref = 'refs/heads/{}'.format(ref)
            quit.commit(
                graph, res, 'New Commit from QuitStore',
                branch_or_ref, ref, query=query
            )
            return '', 200
        except Exception as e:
            # query ok, but unsupported query type or other problem during commit
            logger.exception(e)
            return make_response('Error after executing the update query.', 400)

    if queryType in ['SelectQuery', 'DescribeQuery', 'AskQuery', 'ConstructQuery']:
        res = graph.query(parsedQuery)

    try:
        if queryType in ['SelectQuery', 'AskQuery']:
            return create_result_response(res, resultSetMimetypes[mimetype])
        elif queryType in ['ConstructQuery', 'DescribeQuery']:
            return create_result_response(res, rdfMimetypes[mimetype])
    except KeyError as e:
        return make_response("Mimetype: {} not acceptable".format(mimetype), 406)


@endpoint.route("/provenance", methods=['POST', 'GET'])
@feature_required(Feature.Provenance)
def provenance():
    """Process a SPARQL query (Select only) against Provenance endpoint.

    Returns:
        HTTP Response with query result: If query was a valid select query.
        HTTP Response 200: If request contained a valid update query.
        HTTP Response 400: If request doesn't contain a valid sparql query.
        HTTP Response 406: If accept header is not acceptable.
    """
    quit = current_app.config['quit']

    q = request.values.get('query', None)
    logger.info('Received provenance query: {}'.format(q))

    if 'Accept' in request.headers:
        mimetype = parse_accept_header(request.headers['Accept']).best
    else:
        mimetype = '*/*'

    if q:
        try:
            queryType, parsedQuery = parse_query_type(q)
        except UnSupportedQueryType as e:
            logger.exception(e)
            return make_response('Unsupported Query Type', 400)

        graph = quit.store.store

        if queryType not in ['SelectQuery', 'AskQuery', 'ConstructQuery', 'DescribeQuery']:
            return make_response('Unsupported Query Type', 400)

        res = graph.query(q)

        try:
            if queryType in ['SelectQuery', 'AskQuery']:
                return create_result_response(res, resultSetMimetypes[mimetype])
            elif queryType in ['ConstructQuery', 'DescribeQuery']:
                return create_result_response(res, rdfMimetypes[mimetype])
        except KeyError as e:
            return make_response("Mimetype: {} not acceptable".format(mimetype), 406)
    else:
        if mimetype == 'text/html':
            return render_template('provenance.html')


def create_result_response(res, mimetype):
    """Create a response with the requested serialization."""
    response = make_response(
        res.serialize(format=mimetype[1]),
        200
    )
    response.headers['Content-Type'] = mimetype[0]
    return response


def negotiate(accept_header):
    """Get the mime type and result format for a Accept Header."""
    formats = {
        'application/rdf+xml': 'xml',
        'text/turtle': 'turtle',
        'application/n-triples': 'nt',
        'application/n-quads': 'nquads'
    }
    best = request.accept_mimetypes.best_match(
        ['application/n-triples', 'application/rdf+xml', 'text/turtle', 'application/n-quads']
    )
    # Return json as default, if no mime type is matching
    if best is None:
        best = 'text/turtle'

    return (best, formats[best])


def edit_store(quit, branch_or_ref, ref, method, args, body, mimetype, accept_header, graph):

    def get_where(graph, args):
        s, p, o, c = _spoc(args)

        result = ConjunctiveGraph()

        for subgraph in (
            x for x in graph.store.contexts((s, p, o)) if c is None or x.identifier == c
        ):
            result.addN((s, p, o, subgraph.identifier)
                        for s, p, o in subgraph.triples((None, None, None)))
        return result

    def copy_where(target, graph, args):
        s, p, o, c = _spoc(args)

        for subgraph in (x for x in graph.contexts()):
            target.store.addN((s, p, o, subgraph.identifier)
                              for s, p, o in subgraph.triples((None, None, None)))

    def remove_where(graph, args):
        s, p, o, c = _spoc(args)
        graph.store.remove((s, p, o, c))

    def clear_where(graph, args):
        _, _, _, c = _spoc(args)
        graph.store.remove_context(c)

    def _spoc(args):
        from rdflib import URIRef
        s = args.get('subj', None)
        p = args.get('pred', None)
        o = args.get('obj', None)
        c = args.get('context', None)
        if c:
            c = URIRef(c)
        return s, p, o, c

    try:
        if method in ['GET', 'HEAD']:
            # format, content_type = self.negotiate(self.RESULT_GRAPH, accept_header)

            content_type, format = negotiate(accept_header)
            if content_type.startswith('text/'):
                content_type += "; charset=utf-8"
            headers = {"Content-type": content_type}
            response = (200, headers, get_where(graph, args).serialize(format=format))

        elif method == 'DELETE':
            remove_where(graph, args)
            response = (200, dict(), None)

            quit.commit(graph, 'New Commit from QuitStore', branch_or_ref, ref)

        elif method in ['POST', 'PUT']:

            data = ConjunctiveGraph()
            data.parse(data=body, format="nquads")

            if method == 'POST':
                copy_where(graph, data, args)
                response = (200, dict(), None)

            elif method == 'PUT':
                clear_where(graph, args)
                copy_where(graph, data, args)
                response = (200, dict(), None)

            quit.commit(graph, 'New Commit from QuitStore', branch_or_ref, ref)

        else:
            response = (405, {"Allow": "GET, HEAD, POST, PUT, DELETE"},
                        "Method %s not supported" % method)

    except Exception as e:
        logger.exception(e)
        response = (400, dict(), "<pre>{}</pre>".format(traceback.format_exc()))

    return response


@endpoint.route(
    "/statements", defaults={'branch_or_ref': None},
    methods=['GET', 'POST', 'PUT', 'DELETE']
)
@endpoint.route("/statements/<branch_or_ref>", methods=['GET', 'POST', 'PUT', 'DELETE'])
def statements(branch_or_ref):

    quit = current_app.config['quit']
    default_branch = quit.config.getDefaultBranch()

    if not branch_or_ref and not quit.repository.is_empty:
        branch_or_ref = default_branch

    ref = request.values.get('ref', None) or default_branch
    ref = 'refs/heads/{}'.format(ref)

    method = request.method
    mimetype = request.mimetype
    args = request.args
    body = request.data.decode('utf-8')

    if 'Accept' in request.headers:
        mimetype = parse_accept_header(request.headers['Accept']).best
    else:
        mimetype = 'application/sparql-results+json'

    result = edit_store(
        quit=quit,
        branch_or_ref=branch_or_ref,
        ref=ref,
        method=method,
        args=args,
        body=body,
        mimetype=mimetype,
        accept_header=request.headers.get("Accept"),
        graph=quit.instance(branch_or_ref)
    )
    code, headers, body = result

    response = make_response(body or '', code)
    for k, v in headers.items():
        response.headers[k] = v
    return response
