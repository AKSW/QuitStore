import re

from rdflib.serializer import Serializer
from flask import Blueprint, flash, redirect, request, url_for, current_app, make_response, Markup
from quit.web.app import render_template

from werkzeug.http import parse_accept_header
import sys, traceback

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
    if not branch_or_ref:
        branch_or_ref= 'master'

    quit = current_app.config['quit']

    q = request.values.get('query', None)
    if not q:
        q = request.values.get('update', None)

    if 'Accept' in request.headers:
        mimetype = parse_accept_header(request.headers['Accept']).best
    else:
        mimetype = 'text/html'
        
    ref = request.values.get('ref', None)
    if not ref:
        ref = 'refs/heads/master'

    if q:
        try:
            query_type = parse_query_type(q)
            graph = quit.instance(branch_or_ref)

            content = graph.store.serialize(format='trig').decode()
            for line in (content.splitlines()):
                print(line)

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
                quit.commit(graph, 'New Commit from QuitStore', ref, query=q)          
                return '', 200
            
        except Exception as e:
            current_app.logger.error(e)
            current_app.logger.error(traceback.format_exc())
            return "<pre>"+traceback.format_exc()+"</pre>", 400
    else:
        return render_template('sparql.html')

@endpoint.route("/add", methods=['POST'])
def add():
    """Add nquads to the store.

    Returns:
        HTTP Response 201: If data was processed (even if no data was added)
        HTTP Response: 403: If Request contains non valid nquads
    """
    try:
        data = checkrequest(request)
    

        for graphuri in data['graphs']:
            if not store.graphexists(graphuri):
                logger.debug('Graph ' + graphuri + ' is not part of the store')
                return '', status.HTTP_403_FORBIDDEN

        addtriples(data)

        return '', 201
    except:
        return '', 403


@endpoint.route("/delete", methods=['POST'])
def delete():
    """Delete nquads from the store.

    Returns:
        HTTP Response 201: If data was processed (even if no data was deleted)
        HTTP Response: 403: If Request contains non valid nquads
    """
    try:
        values = checkrequest(request)
    

        for graphuri in values['graphs']:
            if not store.graphexists(graphuri):
                logger.debug('Graph ' + graphuri + ' is not part of the store')
                return '', status.HTTP_403_FORBIDDEN

        deletetriples(values)

        return '', 201
    except:
        return '', 403