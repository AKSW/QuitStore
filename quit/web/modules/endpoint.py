import re

from flask import Blueprint, flash, redirect, request, url_for, current_app
from quit.web.app import render_template

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

@endpoint.route("/sparql", defaults={'branch_or_ref': 'master'}, methods=['POST', 'GET'])
@endpoint.route("/sparql/<branch_or_ref>", methods=['POST', 'GET'])
def sparql(branch_or_ref):
    """Process a SPARQL query (Select or Update).

    Returns:
        HTTP Response with query result: If query was a valid select query.
        HTTP Response 200: If request contained a valid update query.
        HTTP Response 400: If request doesn't contain a valid sparql query.
    """
    quit = current_app.config['quit']

    try:
        q = request.values.get('query', None)
        if not q:
            q = request.values.get('update', None)

        ref = request.values.get('ref', None) or 'refs/heads/master'

        res = ""
        if q:
            query_type = parse_query_type(q)
            graph = quit.instance(branch_or_ref)

            if query_type in ['SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE']:
                res = graph.query(q)
            else:
                res = graph.update(q)                            
                quit.commit(graph, "Test Query", ref, query=q)
            
        context = {
            'result': res,
            'query': q,
        }

        return render_template('sparql.html', **context)    
    except Exception as e:
        print(e)
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