from flask import request, url_for, Response
from flask.ext.api.decorators import set_parsers
from flask.ext.api import FlaskAPI, status, exceptions
from flask.ext.cors import CORS
from FlaskApiParser import *
import yaml, json
from rdflib import Graph
from rfc3987 import parse
from quitFiles import *
import handleexit

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
        if store.graphexists(graphuri) == False:
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
    graphsInRequest = set()
    reqdata = request.data
    test = ConjunctiveGraph()
    try:
        graph.parse(data=reqdata, format='nquads')
    except:
        raise

    quads = graph.quads((None, None, None, None))
    data = splitinformation(quads, graph)

    return data

def addtriples(values):
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

    store.addquads(values['GraphObject'].quads((None,None,None,None)))

    return

def deletetriples(values):
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

    #store.removequads(values['GraphObject'].quads((None,None,None,None)))

    return

def savedexit():
    """This is the method called from exit handler.

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
        if request.method == 'GET':
            if 'query' in request.args:
                query = request.args['query']
        elif request.method == 'POST':
            if 'query' in request.form:
                query = request.form['query']
    except:
        print('Query is missing in request')
        return '', status.HTTP_400_BAD_REQUEST

    try:
        result = store.processsparql(query)
    except:
        print('Something is wrong with received query')
        return '', status.HTTP_400_BAD_REQUEST

    # Check weather we have a result (SELECT) or not (UPDATE) and respond correspondingly
    if result != None:
        return sparqlresponse(result)
    else:
        return '', status.HTTP_200_OK


@app.route("/checkout", methods=['POST'])
def checkoutVersion():
    """Receive a HTTP request with a commit id and initialize store with data from this commit.

    Returns:
        HTTP Response 200: If commit id is valid and store is reinitialized with the data.
        HTTP Response 400: If commit id is not valid.
    """
    return

@app.route("/commits", methods=['GET'])
def getCommits():
    """Receive a HTTP request and reply with all known commits.

    Returns:
        HTTP Response: json containing id, committeddate and message.
    """
    data = gitrepo.getcommits()
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
        commitrepo()

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
                return [note_repr(idx) for idx in sorted(notes.keys())], status.HTTP_403_FORBIDDEN

        deletetriples(values)
        commitrepo()

        return '', status.HTTP_201_CREATED
    else:
        return '', status.HTTP_403_FORBIDDEN

def main():
    app.run(debug=True, use_reloader=True)

if __name__ == '__main__':
    store = initializegraphs()
    # The app is started with an exit handler
    with handleexit.handle_exit(savedexit()):
        main()
