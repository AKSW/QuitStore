import traceback

import logging
from flask import Blueprint, request, current_app, make_response
from rdflib import ConjunctiveGraph
from quit.conf import Feature
from quit import helpers as helpers
from quit.helpers import parse_sparql_request, parse_query_type
from quit.web.app import render_template, feature_required
from quit.exceptions import UnSupportedQuery, SparqlProtocolError, NonAbsoluteBaseError
from quit.exceptions import FromNamedError, QuitMergeConflict, RevisionNotFound
import datetime
import uuid
import base64

logger = logging.getLogger('quit.modules.endpoint')

__all__ = ('endpoint')

endpoint = Blueprint('endpoint', __name__)
resultSetMimetypesDefault = 'application/sparql-results+xml'
askMimetypesDefault = 'application/sparql-results+xml'
rdfMimetypesDefault = 'text/turtle'

resultSetMimetypes = ['application/sparql-results+xml', 'application/xml',
                      'application/sparql-results+json', 'application/json', 'text/csv',
                      'text/html', 'application/xhtml+xml']
askMimetypes = ['application/sparql-results+xml', 'application/xml',
                'application/sparql-results+json', 'application/json', 'text/html',
                'application/xhtml+xml']
rdfMimetypes = ['text/turtle', 'application/x-turtle', 'application/rdf+xml', 'application/xml',
                'application/n-triples', 'application/trig', 'application/json-ld',
                'application/json']

result_serializations = {
    'application/sparql-results+xml': 'xml',
    'application/xml': 'xml',
    'application/sparql-results+json': 'json',
    'application/json': 'json',
    'text/csv': 'csv',
    'text/html': 'html',
    'application/xhtml+xml': 'html',
}

rdf_serializations = {
    'text/turtle': 'turtle',
    'application/x-turtle': 'turtle',
    'text/csv': 'csv',
    'text/html': 'html',
    'application/xhtml+xml': 'html',
    'application/sparql-results+xml': 'xml',
    'application/xml': 'xml',
    'application/rdf+xml': 'xml',
    'application/sparql-results+json': 'json',
    'application/json': 'json-ld',
    'application/json-ld': 'json-ld',
    'application/n-triples': 'nt',
    'application/trig': 'trig'
}


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
    default_branch = quit.getDefaultBranch()

    if not branch_or_ref and not quit.repository.is_empty:
        branch_or_ref = default_branch

    logger.debug("Request method: {}".format(request.method))

    query, type, default_graph, named_graph = parse_sparql_request(request)

    if query is None:
        if request.accept_mimetypes.best_match(['text/html']) == 'text/html':
            return render_template('sparql.html', current_ref=branch_or_ref or default_branch,
                                   mode='query')
        else:
            return make_response('No Query was specified or the Content-Type is not set according' +
                                 'to the SPARQL 1.1 standard', 400)
    else:
        # TODO allow USING NAMED when fixed in rdflib
        if len(named_graph) > 0:
            return make_response('FROM NAMED and USING NAMED not supported, yet', 400)

        parse_type = getattr(helpers, 'parse_' + type + '_type')

        try:
            queryType, parsedQuery = parse_type(
                query, quit.config.namespace, default_graph, named_graph)
        except UnSupportedQuery:
            return make_response('Unsupported Query', 400)
        except NonAbsoluteBaseError:
            return make_response('Non absolute Base URI given', 400)
        except SparqlProtocolError:
            return make_response('Sparql Protocol Error', 400)

    if queryType in ['InsertData', 'DeleteData', 'Modify', 'DeleteWhere', 'Load']:
        if branch_or_ref:
            commit_id = quit.repository.revision(branch_or_ref).id
        else:
            commit_id = None

        parent_commit_id = request.values.get('parent_commit_id', None) or None
        if parent_commit_id and parent_commit_id != commit_id:
            resolution_method = request.values.get('resolution_method', None) or None
            if resolution_method == "reject":
                logger.debug("rejecting update because {} is at {} but {} was expected".format(
                             branch_or_ref, commit_id, parent_commit_id))
                return make_response('reject', 409)  # alternative 412
            elif resolution_method in ("merge", "branch"):
                logger.debug(("writing update to a branch of {} because it is at {} but {} was "
                             "expected").format(branch_or_ref, commit_id, parent_commit_id))
                try:
                    quit.repository.lookup(parent_commit_id)
                except RevisionNotFound:
                    return make_response("The provided parent commit (parent_commit_id={}) "
                                         "could not be found.".format(parent_commit_id), 400)

                time = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
                shortUUID = (base64.urlsafe_b64encode(uuid.uuid1().bytes).decode("utf-8")
                             ).rstrip('=\n').replace('/', '_')
                target_branch = "tmp/{}_{}".format(time, shortUUID)
                target_ref = "refs/heads/" + target_branch
                logger.debug("target ref is: {}".format(target_ref))
                oid = quit.applyQueryOnCommit(parsedQuery, parent_commit_id, target_ref,
                                              query=query, default_graph=default_graph,
                                              named_graph=named_graph)

                if resolution_method == "merge":
                    logger.debug(("going to merge update into {} because it is at {} but {} was "
                                 "expected").format(branch_or_ref, commit_id, parent_commit_id))
                    try:
                        quit.repository.merge(target=branch_or_ref, branch=target_ref)
                        oid = quit.repository.revision(branch_or_ref).id
                        # delete temporary branch
                        tmp_branch = quit.repository._repository.branches.get(target_branch)
                        tmp_branch.delete()
                        response = make_response('success', 200)
                        target_branch = branch_or_ref
                    except QuitMergeConflict as e:
                        response = make_response('merge failed', 400)
                else:
                    response = make_response('branched', 200)
                response.headers["X-CurrentBranch"] = target_branch
                response.headers["X-CurrentCommit"] = oid
                return response

                # Add info about temporary branch
        else:
            graph, commitid = quit.instance(parent_commit_id)

            target_head = request.values.get('target_head', branch_or_ref) or default_branch
            target_ref = 'refs/heads/{}'.format(target_head)
            try:
                oid = quit.applyQueryOnCommit(parsedQuery, branch_or_ref, target_ref,
                                              query=query, default_graph=default_graph,
                                              named_graph=named_graph)
                response = make_response('', 200)
                response.headers["X-CurrentBranch"] = target_head
                if oid is not None:
                    response.headers["X-CurrentCommit"] = oid
                else:
                    response.headers["X-CurrentCommit"] = commitid
                return response
            except Exception as e:
                # query ok, but unsupported query type or other problem during commit
                logger.exception(e)
                return make_response('Error after executing the update query.', 400)
    elif queryType in ['SelectQuery', 'DescribeQuery', 'AskQuery', 'ConstructQuery']:
        try:
            graph, commitid = quit.instance(branch_or_ref)
        except Exception as e:
            logger.exception(e)
            return make_response('No branch or reference given.', 400)

        try:
            res = graph.query(parsedQuery)
        except FromNamedError:
            return make_response('FROM NAMED not supported, yet', 400)
        except UnSupportedQuery:
            return make_response('Unsupported Query', 400)

        mimetype = _getBestMatchingMimeType(request, queryType)

        if not mimetype:
            return make_response("Mimetype: {} not acceptable".format(mimetype), 406)

        if queryType in ['SelectQuery', 'AskQuery']:
            serializations_by_sparql_type = result_serializations
        else:
            serializations_by_sparql_type = rdf_serializations

        response = create_result_response(res, mimetype, serializations_by_sparql_type[mimetype])
        if branch_or_ref:
            response.headers["X-CurrentBranch"] = branch_or_ref
        if commitid:
            response.headers["X-CurrentCommit"] = commitid
        return response
    else:
        logger.debug("Unsupported Type: {}".format(queryType))
        return make_response("Unsupported Query Type: {}".format(queryType), 400)


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

    query, type, default_graph, named_graph = parse_sparql_request(request)
    logger.info('Received provenance query: {}'.format(query))

    if query is not None and type == 'query':
        if len(named_graph) > 0:
            return make_response('Unsupported Query, "FROM NAMED not supported, yet"', 400)
        try:
            queryType, parsedQuery = parse_query_type(query)
        except UnSupportedQuery:
            return make_response('Unsupported Query', 400)
        except NonAbsoluteBaseError:
            return make_response('Non absolute Base URI given', 400)
        except SparqlProtocolError:
            return make_response('Sparql Protocol Error', 400)

        graph = quit.store.store

        if queryType not in ['SelectQuery', 'AskQuery', 'ConstructQuery', 'DescribeQuery']:
            return make_response('Unsupported Query Type', 400)

        res = graph.query(query)

        mimetype = _getBestMatchingMimeType(request, queryType)

        if not mimetype:
            return make_response("Mimetype: {} not acceptable".format(mimetype), 406)

        if queryType in ['SelectQuery', 'AskQuery']:
            serializations_by_sparql_type = result_serializations
        else:
            serializations_by_sparql_type = rdf_serializations

        return create_result_response(res, mimetype, serializations_by_sparql_type[mimetype])
    else:
        if request.accept_mimetypes.best_match(['text/html']) == 'text/html':
            return render_template('sparql.html', mode='provenance')


def _getBestMatchingMimeType(request, queryType):
    if queryType == 'SelectQuery':
        mimetype_default = resultSetMimetypesDefault
        mimetype_list = resultSetMimetypes
    elif queryType == 'AskQuery':
        mimetype_default = askMimetypesDefault
        mimetype_list = askMimetypes
    elif queryType in ['ConstructQuery', 'DescribeQuery']:
        mimetype_default = rdfMimetypesDefault
        mimetype_list = rdfMimetypes

    match_list = [mimetype_default] + mimetype_list
    if 'Accept' in request.headers:
        mimetype = request.accept_mimetypes.best_match(match_list, None)
    else:
        mimetype = mimetype_default

    return mimetype


def create_result_response(res, mimetype, serialization):
    """Create a response with the requested serialization."""
    response = make_response(res.serialize(format=serialization), 200)
    response.headers['Content-Type'] = mimetype
    return response


def edit_store(quit, branch_or_ref, ref, method, args, body, graph):

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
            headers = {"Content-type": 'application/n-quads'}
            response = (200, headers, get_where(graph, args).serialize(format='nquads'))

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
    args = request.args
    body = request.data.decode('utf-8')

    graph, commitid = quit.instance(branch_or_ref)

    result = edit_store(
        quit=quit,
        branch_or_ref=branch_or_ref,
        ref=ref,
        method=method,
        args=args,
        body=body,
        graph=graph
    )
    code, headers, body = result

    response = make_response(body or '', code)
    for k, v in headers.items():
        response.headers[k] = v
    if commitid:
        response.headers["X-CurrentCommit"] = commitid
    return response
