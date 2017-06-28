import sys, traceback
import re

from werkzeug.http import parse_accept_header
from flask import Blueprint, flash, redirect, request, url_for, current_app, make_response, Markup
from rdflib import ConjunctiveGraph
from quit.conf import STORE_PROVENANCE, STORE_DATA
from quit.web.app import render_template, storemode_required
from quit.exceptions import UnSupportedQueryType

__all__ = [ 'endpoint' ]

endpoint = Blueprint('endpoint', __name__)

pattern = re.compile(r"""
    (?P<queryType>(CONSTRUCT|SELECT|ASK|DESCRIBE|INSERT|DELETE|CREATE|CLEAR|DROP|LOAD|COPY|MOVE|ADD))
    """, re.VERBOSE | re.IGNORECASE)

def parse_query_type(query):
    try:
        query_type = pattern.search(query).group("queryType").upper()
    except AttributeError:
        query_type = None    
    return query_type

@endpoint.route("/sparql", defaults={'branch_or_ref': None}, methods=['POST', 'GET'])
@endpoint.route("/sparql/<branch_or_ref>", methods=['POST', 'GET'])
def sparql(branch_or_ref):
    """Process a SPARQL query (Select or Update).

    Returns:
        HTTP Response with query result: If query was a valid select query.
        HTTP Response 200: If request contained a valid update query.
        HTTP Response 400: If request doesn't contain a valid sparql query.
    """
    quit = current_app.config['quit']
    default_branch = quit.config.getDefaultBranch() or 'master'

    if not branch_or_ref and not quit.repository.is_empty:
        branch_or_ref = default_branch

    q = request.values.get('query', None) or request.values.get('update', None)
    ref = request.values.get('ref', None) or 'refs/heads/%s' % default_branch

    if 'Accept' in request.headers:
        mimetype = parse_accept_header(request.headers['Accept']).best
    else:
        mimetype = 'text/html'        

    if q:
        try:
            query_type = parse_query_type(q)
            graph = quit.instance(branch_or_ref)

            if query_type in ['SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE']:
                res = graph.query(q)

                if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
                    results = res.serialize(format='html')
                    response=make_response(render_template("results.html", results = Markup(results.decode())))
                    response.headers['Content-Type'] = 'text/html'
                    return response
                elif mimetype in ['application/json', 'application/sparql-results+json']:
                    response = make_response(res.serialize(format='json'),200)
                    response.headers['Content-Type'] = 'application/json'
                    return response
                elif mimetype in ['application/rdf+xml','application/xml', 'application/sparql-results+xml']:
                    response = make_response(res.serialize(format='xml'),200)
                    response.headers['Content-Type'] = 'application/rdf+xml'
                    return response
                elif mimetype in ['application/csv','text/csv']:
                    response = make_response(res.serialize(format='csv'),200)
                    response.headers['Content-Type'] = 'text/csv'
                    return response     
            else:
                res = graph.update(q)                          
                quit.commit(graph, 'New Commit from QuitStore', branch_or_ref, ref, query=q)          
                return '', 200
            
        except Exception as e:
            current_app.logger.error(e)
            current_app.logger.error(traceback.format_exc())
            return "<pre>"+traceback.format_exc()+"</pre>", 400
    else:
        return render_template('sparql.html')

@endpoint.route("/provenance", methods=['POST', 'GET'])
@storemode_required(STORE_PROVENANCE)
def provenance():
    """Process a SPARQL query (Select only) against Provenance endpoint.

    Returns:
        HTTP Response with query result: If query was a valid select query.
        HTTP Response 200: If request contained a valid update query.
        HTTP Response 400: If request doesn't contain a valid sparql query.
    """
    quit = current_app.config['quit']

    q = request.values.get('query', None)

    if 'Accept' in request.headers:
        mimetype = parse_accept_header(request.headers['Accept']).best
    else:
        mimetype = 'text/html'
        
    if q:
        try:
            query_type = parse_query_type(q)
            graph = quit.store.store

            if query_type in ['SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE']:
                res = graph.query(q)

                if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
                    results = res.serialize(format='html')
                    response=make_response(render_template("results.html", results = Markup(results.decode())))
                    response.headers['Content-Type'] = 'text/html'
                    return response
                elif mimetype in ['application/json', 'application/sparql-results+json']:
                    response = make_response(res.serialize(format='json'),200)
                    response.headers['Content-Type'] = 'application/json'
                    return response
                elif mimetype in ['application/rdf+xml','application/xml', 'application/sparql-results+xml']:
                    response = make_response(res.serialize(format='xml'),200)
                    response.headers['Content-Type'] = 'application/rdf+xml'
                    return response
                elif mimetype in ['application/csv','text/csv']:
                    response = make_response(res.serialize(format='csv'),200)
                    response.headers['Content-Type'] = 'text/csv'
                    return response   
            else:
                raise UnSupportedQueryType()
            
        except Exception as e:
            current_app.logger.error(e)
            current_app.logger.error(traceback.format_exc())
            return "<pre>"+traceback.format_exc()+"</pre>", 400
    else:
        return render_template('provenance.html')

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
        s,p,o,c = _spoc(args)
        
        result = ConjunctiveGraph()

        for subgraph in (x for x in graph.store.contexts((s,p,o)) if c is None or x.identifier == c):
            result.addN((s, p, o, subgraph.identifier) for s, p, o in subgraph.triples((None, None, None)))
        return result

    def copy_where(target, graph, args):
        s,p,o,c = _spoc(args)

        for subgraph in (x for x in graph.contexts()): #if c is None or x.identifier == c):
            target.store.addN((s, p, o, subgraph.identifier) for s, p, o in subgraph.triples((None, None, None)))
    
    def remove_where(graph, args):
        s,p,o,c = _spoc(args)
        graph.store.remove((s, p, o, c))

    def clear_where(graph, args):
        _,_,_,c = _spoc(args)
        graph.store.remove_context(c)

    def serialize(graph, format_):
        format_,mimetype_=mimeutils.format_to_mime(format_)
        response=make_response(graph.serialize(format=format_))
        response.headers["Content-Type"]=mimetype_
        return response

    def _spoc(args):
        from rdflib import URIRef
        s = args.get('subj', None)
        p = args.get('pred', None)
        o = args.get('obj', None)
        c = args.get('context', None)
        if c: c = URIRef(c)
        return s, p, o, c

    try:
        if method in ['GET', 'HEAD']:
            #format, content_type = self.negotiate(self.RESULT_GRAPH, accept_header)
            #if content_type.startswith('text/'): content_type += "; charset=utf-8"

            content_type, format = negotiate(accept_header)
            if content_type.startswith('text/'): content_type += "; charset=utf-8"
            print(format)
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
            response = (405, {"Allow": "GET, HEAD, POST, PUT, DELETE"}, "Method %s not supported" % method)

    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        response = (400, dict(), "<pre>"+traceback.format_exc()+"</pre>")

    return response

@endpoint.route("/statements", defaults={'branch_or_ref': None}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@endpoint.route("/statements/<branch_or_ref>", methods=['GET', 'POST', 'PUT', 'DELETE'])
def statements(branch_or_ref):

    quit = current_app.config['quit']
    default_branch = quit.config.getDefaultBranch() or 'master'

    if not branch_or_ref and not quit.repository.is_empty:
        branch_or_ref = default_branch

    ref = request.values.get('ref', None) or 'refs/heads/%s' % default_branch

    method = request.method
    mimetype = request.mimetype
    args = request.args
    body = request.data.decode('utf-8')

    print('%s %s %s %s' % (method, mimetype, args, body))

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