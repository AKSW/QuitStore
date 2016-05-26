#!/usr/bin/env python3

from flask import request, Response
from flask.ext.api.decorators import set_parsers
from flask.ext.api import FlaskAPI, status
from flask.ext.cors import CORS
from rdflib import ConjunctiveGraph
from FlaskApiParser import NQuadsParser
import json
from quitFiles import MemoryStore, sparqlresponse, splitinformation
from FileReference import FileReference
import handleexit
import sys

app = FlaskAPI(__name__)
CORS(app)


def initializegraphs():
    """Build all needed objects.

    Returns:
        A dictionary containing the store object and git repo object.

    """
    store = MemoryStore()

    versioning = True
    graphs = store.getgraphsfromconf()
    for graphuri, filename in graphs.items():
        if store.graphexists(graphuri) is False:
            graph = FileReference(filename, versioning)
            store.addFile(graphuri, graph)
            print('Success: Graph with URI: ' + graphuri + ' added to my known graphs list')

    return store


def checkrequest(request):
    """Analyze RDF data contained in a POST request.

    Args:
        request: A Flask HTTP Request.
    Returns:
        data: A list with RDFLib.quads object and the rdflib.ConjunciveGraph object
    Raises:
        Exception: I contained data is not valid nquads.

    """
    data = []
    reqdata = request.data
    graph = ConjunctiveGraph()

    try:
        graph.parse(data=reqdata, format='nquads')
    except:
        raise

    quads = graph.quads((None, None, None, None))
    data = splitinformation(quads, graph)

    return data


def addtriples(values):
    """Add triples to the store.

    Args:
        values: A dictionary containing quads and a graph object
    Raises:
        Exception: If contained data is not valid.
    """
    for data in values['data']:
        # delete all triples that should be added
        currentgraph = store.getgraphobject(data['graph'])
        currentgraph.deletequad(data['quad'])

    for data in values['data']:
        # and now add them
        currentgraph = store.getgraphobject(data['graph'])
        currentgraph.addquads(data['quad'])

    # sort files that took part and save them
    for graph in values['graphs']:
        print('Trying to save graph with URI: ' + graph)
        currentgraph = store.getgraphobject(graph)
        currentgraph.sortfile()
        currentgraph.savefile()

    store.addquads(values['GraphObject'].quads((None, None, None, None)))

    return


def deletetriples(values):
    """Delete triples from the store.

    Args:
        values: A dictionary containing quads and a graph object
    Raises:
        Exception: If contained data is not valid.
    """
    for data in values['data']:
        # delete all triples that should be added
        currentgraph = store.getgraphobject(data['graph'])
        currentgraph.deletequad(data['quad'])

    # sort files that took part and save them
    for graph in values['graphs']:
        print('Trying to save graph with URI: ' + graph)
        currentgraph = store.getgraphobject(graph)
        currentgraph.sortfile()
        currentgraph.savefile()
        store.reinitgraph(graph)

    # store.removequads(values['GraphObject'].quads((None,None,None,None)))

    return


def savedexit():
    """Perform actions to be exevuted on API shutdown.

    Add methods you want to call on unexpected shutdown.
    """
    store.exit()

    return

'''
API
'''


@app.route("/sparql", methods=['POST', 'GET'])
def sparql():
    """Process a SPARQL query (Select or Update).

    Returns:
        HTTP Response with query result: If query was a valid select query.
        HTTP Response 200: If request contained a valid update query.
        HTTP Response 400: If request doesn't contain a valid sparql query.
    """
    try:
        # TODO: also handle 'default-graph-uri'
        if request.method == 'GET':
            if 'query' in request.args:
                query = request.args['query']
            elif 'update' in request.args:
                query = request.form['update']
        elif request.method == 'POST':
            if 'query' in request.form:
                query = request.form['query']
            elif 'update' in request.form:
                query = request.form['update']
        else:
            print("unknown request method:", request.method)
            return '', status.HTTP_400_BAD_REQUEST
    except:
        print('Query is missing in request')
        return '', status.HTTP_400_BAD_REQUEST

    try:
        result = store.processsparql(query)
    except:
        print('Something is wrong with received query')
        return '', status.HTTP_400_BAD_REQUEST

    # Check weather we have a result (SELECT) or not (UPDATE) and respond correspondingly
    if result is not None:
        return sparqlresponse(result, resultFormat())
    else:
        print("empty")
        return Response("",
                        content_type=resultFormat()['mime']
                        )
        # return '', status.HTTP_200_OK


@app.route("/git/checkout", methods=['POST'])
def checkoutVersion():
    """Receive a HTTP request with a commit id and initialize store with data from this commit.

    Returns:
        HTTP Response 200: If commit id is valid and store is reinitialized with the data.
        HTTP Response 400: If commit id is not valid.
    """
    if 'commitid' in request.form:
        commitid = request.form['commitid']
    else:
        print('Commit id is missing in request')
        return '', status.HTTP_400_BAD_REQUEST

    print('COmmit-ID', commitid)
    if store.commitexists(commitid):
        store.checkout(commitid)
    else:
        print('Not a valid commit id')
        return '', status.HTTP_400_BAD_REQUEST

    return '', status.HTTP_200_OK


@app.route("/git/log", methods=['GET'])
def getCommits():
    """Receive a HTTP request and reply with all known commits.

    Returns:
        HTTP Response: json containing id, committeddate and message.
    """
    data = store.getcommits()
    resp = Response(json.dumps(data), status=200, mimetype='application/json')
    return resp


@app.route("/add", methods=['POST'])
@set_parsers(NQuadsParser)
def addTriple():
    """Add nquads to the store.

    Returns:
        HTTP Response 201: If data was processed (even if no data was added)
        HTTP Response: 403: If Request contains non valid nquads
    """
    if request.method == 'POST':
        try:
            data = checkrequest(request)
        except:
            return '', status.HTTP_403_FORBIDDEN

        for graphuri in data['graphs']:
            if not store.graphexists(graphuri):
                print('Graph ' + graphuri + ' is not part of the store')
                return '', status.HTTP_403_FORBIDDEN

        addtriples(data)

        return '', status.HTTP_201_CREATED
    else:
        return '', status.HTTP_403_FORBIDDEN


@app.route("/delete", methods=['POST', 'GET'])
@set_parsers(NQuadsParser)
def deleteTriple():
    """Delete nquads from the store.

    Returns:
        HTTP Response 201: If data was processed (even if no data was deleted)
        HTTP Response: 403: If Request contains non valid nquads
    """
    if request.method == 'POST':
        try:
            values = checkrequest(request)
        except:
            return '', status.HTTP_403_FORBIDDEN

        for graphuri in values['graphs']:
            if not store.graphexists(graphuri):
                print('Graph ' + graphuri + ' is not part of the store')
                return '', status.HTTP_403_FORBIDDEN

        deletetriples(values)

        return '', status.HTTP_201_CREATED
    else:
        return '', status.HTTP_403_FORBIDDEN


def resultFormat():
    """Get the mime type and result format for a Accept Header."""
    formats = {
        'application/sparql-results+json': 'json',
        'application/sparql-results+xml': 'xml',
        'application/rdf+xml': 'xml',
        'text/turtle': 'turtle',
        'text/plain': 'nt',
        'application/n-triples': 'nt',
        'application/nquads': 'nquads',
        'application/n-quads': 'nquads'
    }
    best = request.accept_mimetypes.best_match(
        ['application/sparql-results+json', 'application/sparql-results+xml', 'application/rdf+xml', 'text/turtle', 'application/nquads']
    )
    # Return json as default, if no mime type is matching
    if best is None:
        best = 'application/sparql-results+json'

    return {"mime": best, "format": formats[best]}


def main():
    """Start the app."""
    app.run(debug=True, use_reloader=False)

if __name__ == '__main__':
    store = initializegraphs()
    sys.setrecursionlimit(3000)
    # The app is started with an exit handler
    with handleexit.handle_exit(savedexit()):
        main()
