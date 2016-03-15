from flask import request, url_for
from flask.ext.api.decorators import set_parsers
from flask.ext.api import FlaskAPI, status, exceptions
from FlaskApiParser import *
import yaml
from rdflib import Graph
from rfc3987 import parse
from quitFiles import *
import handleexit

app = FlaskAPI(__name__)

notes = {
    0: 'do the shopping',
    1: 'build the codez',
    2: 'paint the door',
}

def initializegraphs():
    store = MemoryStore()

    settings = store.getstoresettings()
    repository = settings['gitrepo']

    versioning = True
    graphs = store.getgraphsfromconf()
    for graphuri, filename in graphs.items():
        if store.graphexists(graphuri) == False:
            graph = FileReference(filename, versioning)
            store.addFile(graphuri, graph)
            print('Success: Graph with URI: ' + graphuri + ' added to my known graphs list')

    return store

def note_repr(key):
    return {
        'url': request.host_url.rstrip('/') + url_for('notes_detail', key=key),
        'text': notes[key]
    }

def processsparql(querystring):
    try:
        query = QueryCheck(querystring)
    except:
        raise Exception()

    if query.getType() == 'SELECT':
        return 'SELECT', store.query(querystring)
    else:
        print('Update-Query')
        return 'UPDATE', store.update(querystring)

def checkrequest(request):
    data = []
    graphsInRequest = set()
    reqdata = request.data
    print('Das kam an', reqdata)
    test = ConjunctiveGraph()
    try:
        test.parse(data=reqdata, format='nquads')
    except:
        raise

    quads = test.quads((None, None, None, None))
    data = splitinformation(quads)

    return data

def addtriples(values):
    backup = {}
    addedtriples = {}

    for data in values['data']:
        # delete all triples that should be added
        currentgraph = store.getgraphobject(data['graph'])
        print('Trying to delete: ' + data['quad'])
        currentgraph.deletetriple(data['quad'])

    for data in values['data']:
        # and now add them
        currentgraph = store.getgraphobject(data['graph'])
        currentgraph.addtriple(data['quad'])

    # sort files that took part and save them
    for graph in values['graphs']:
        print('Trying to save graph with URI: ' + graph)
        currentgraph = store.getgraphobject(graph)
        currentgraph.sortfile()
        currentgraph.savefile()
        currentgraph.commit()

    return

def applychanges(values):
    backup = {}
    addedtriples = {}
    deletetriples = {}

    # to commit a transaction, save the state of graph
    for graph in values['graphs']:
        currentgraph = store.getgraphobject(graph)
        backup[graph] = currentgraph.getcontent()
        print('Trying to save graph with URI: ' + graph)

    for data in values['data']:
        # delete all triples that should be added and keep them in mind
        if data['action'] == 'add':
            addedtriples[data['quad']] = data['graph']
            currentgraph = store.getgraphobject(data['graph'])
            print('Trying to delete: ' + data['quad'])
            currentgraph.deletetriple(data['quad'])
        # collect all triples that should be deleted
        elif data['action'] == 'delete':
            deletetriples[data['quad']] = data['graph']

    # delete all triples that should be deleted
    for triple, graph in deletetriples.items():
        # Check if there are triples that should be deleted but also
        # be added. If so, abort and reset to old state of data
        if triple in list(addedtriples.keys()):
            print("Error: not a valid transaction")
            # discard changes
            for graph in values['graphs']:
                currentgraph = store.getgraphobject(graph)
                currentgraph.setcontent(backup[graph])
            return
        else:
            currentgraph = store.getgraphobject(graph)
            print('Trying to delete: ' + triple)
            currentgraph.deletetriple(triple)

    # add all triples that should be added
    for triple, graph in addedtriples.items():
        currentgraph = store.getgraphobject(graph)
        currentgraph.addtriple(triple, False)

    # sort files that took part and save them
    for graph in values['graphs']:
        print('Trying to save graph with URI: ' + graph)
        currentgraph = store.getgraphobject(graph)
        currentgraph.sortfile()
        currentgraph.savefile()
        currentgraph.commit()

    return

'''
If the store was updated via a SPARQL-Update, we have to update the
content of FileReference too
NOTE: This method will be replaced by a more granular method that get the exact triples
which where added/deleted and will add/delete them in file content.
'''
def updatefilecontent():
    for graphuri, fileobject in store.getgraphs():
        if fileobject.isversioned():
            content = store.getgraphcontent(graphuri)
            fileobject.setcontent(content)
            fileobject.sortfile()
            fileobject.savefile()
            fileobject.commit()

    return

def savegraphs():
    for graphuri, fileobject in store.getgraphs():
        if fileobject.isversioned():
            fileobject.sortfile()
            fileobject.savefile()
            fileobject.commit()

'''
API
'''

@app.route("/sparql/", methods=['POST', 'GET'])
def sparql():
    '''
    Process SPARQL-Query
      - update files on DELETE and UPDATE queries
      - return result on SELECT
    '''
    try:
        if request.method == 'GET':
            if 'query' in request.args:
                query = request.args['query']
        elif request.method == 'POST':
            if 'query' in request.form:
                query = request.form['query']
    except:
        print('Es kam gar keine Query an')
        return '', status.HTTP_400_BAD_REQUEST

    try:
        result = processsparql(query)
        print('Query-Result', result)
    except:
        print('Mit der Query stimmt etwas nicht')
        return '', status.HTTP_400_BAD_REQUEST

    if result[0] == 'SELECT':
        return sparqlresponse(result[1])
    else:
        updatefilecontent()
        return '', status.HTTP_200_OK


@app.route("/add/", methods=['POST', 'GET'])
@set_parsers(NQuadsParser)
def addTriple():
    '''
    List or create notes.
    '''
    if request.method == 'POST':
        print('Post-Request ' + str(request))
        try:
            data = checkrequest(request)
        except:
            return '', status.HTTP_403_FORBIDDEN

        for k, v in data.items():
            print("applychanges : " + k + ':' + str(v) )

        print('Graphliste: ' + str(store.getgraphs()))

        for graphuri in data['graphs']:
            if not store.graphexists(graphuri):
                print('Graph ' + graphuri + ' nicht da')
                return '', status.HTTP_403_FORBIDDEN

        addedtriples = addtriples(data)

        return '', status.HTTP_201_CREATED
    else:
        print('Get-Request ' + str(request))
        values = checkrequest(request)

@app.route("/delete/", methods=['POST', 'GET'])
def deleteTriple():
    '''
    List or create notes.
    '''
    if request.method == 'POST':
        try:
            values = checkrequest(request)
        except:
            return '', status.HTTP_403_FORBIDDEN

        if not deleteFromGraph(values):
            return '', status.HTTP_204_NO_CONTENT

        print('Graphliste: ' + str(store.getgraphs()))
        for graphuri in values['graphs']:
            if not store.graphexists(graphuri):
                print('Graph ' + graphuri + ' nicht da')
                return [note_repr(idx) for idx in sorted(notes.keys())], status.HTTP_403_FORBIDDEN

        deletedtriples = deletetriples(values)

        return '', status.HTTP_201_CREATED
        return note_repr(idx), status.HTTP_201_CREATED

    # request.method == 'GET'
    return [note_repr(idx) for idx in sorted(notes.keys())]


@app.route("/<int:key>/", methods=['GET', 'PUT', 'DELETE'])
def notes_detail(key):
    '''
    Retrieve, update or delete note instances.
    '''
    if request.method == 'PUT':
        note = str(request.data.get('text', ''))
        notes[key] = note
        return note_repr(key)

    elif request.method == 'DELETE':
        notes.pop(key, None)
        return '', status.HTTP_204_NO_CONTENT

    # request.method == 'GET'
    if key not in notes:
        raise exceptions.NotFound()
    return note_repr(key)

def main():
    app.run(debug=True, use_reloader=False)

if __name__ == '__main__':
    with handleexit.handle_exit(savegraphs):
        store = initializegraphs()
        main()
