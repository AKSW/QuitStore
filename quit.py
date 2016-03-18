from flask import request, url_for
from flask.ext.api.decorators import set_parsers
from flask.ext.api import FlaskAPI, status, exceptions
from flask.ext.cors import CORS
from FlaskApiParser import *
import yaml
from rdflib import Graph
from rfc3987 import parse
from quitFiles import *
import handleexit

app = FlaskAPI(__name__)
CORS(app)

def initializegraphs():
    store = MemoryStore()
    gitrepo = GitRepo(store.getstorepath())

    settings = store.getstoresettings()
    repository = settings['gitrepo']

    versioning = True
    graphs = store.getgraphsfromconf()
    for graphuri, filename in graphs.items():
        if store.graphexists(graphuri) == False:
            graph = FileReference(filename, versioning)
            store.addFile(graphuri, graph)
            print('Success: Graph with URI: ' + graphuri + ' added to my known graphs list')

    return {'store':store, 'gitrepo':gitrepo}

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
    test = ConjunctiveGraph()
    try:
        test.parse(data=reqdata, format='nquads')
    except:
        raise

    quads = test.quads((None, None, None, None))
    data = splitinformation(quads, test)

    return data

def addtriples(values):
    for data in values['data']:
        # delete all triples that should be added
        currentgraph = store.getgraphobject(data['graph'])
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

    store.addquads(values['GraphObject'].quads((None,None,None,None)))

    return

def deletetriples(values):
    for data in values['data']:
        # delete all triples that should be added
        currentgraph = store.getgraphobject(data['graph'])
        currentgraph.deletetriple(data['quad'])

    # sort files that took part and save them
    for graph in values['graphs']:
        print('Trying to save graph with URI: ' + graph)
        currentgraph = store.getgraphobject(graph)
        currentgraph.sortfile()
        currentgraph.savefile()
        store.reinitgraph(graph)

    #store.removequads(values['GraphObject'].quads((None,None,None,None)))

    return

'''
If the store was updated via a SPARQL-Update, we have to update the
content of FileReference too
NOTE: This method will be replaced by a more granular method that get the exact triples
which where added/deleted and will add/delete them in file content.
'''
def updatefilecontent(query):
    for graphuri, fileobject in store.getgraphs():
        content = store.getgraphcontent(graphuri)
        fileobject.setcontent(content)
        fileobject.sortfile()
        fileobject.savefile()

    gitrepo.update()
    try:
        gitrepo.commit(message='SPARQL Update\n\n' + query)
    except:
        pass

    return

def commitrepo():
    gitrepo.update()
    gitrepo.commit()

    return

def savegraphs():
    for graphuri, fileobject in store.getgraphs():
        if fileobject.isversioned():
            fileobject.sortfile()
            fileobject.savefile()

    gitrepo.update()
    gitrepo.commit()

    return

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
    except:
        print('Mit der Query stimmt etwas nicht')
        return '', status.HTTP_400_BAD_REQUEST

    if result[0] == 'SELECT':
        return sparqlresponse(result[1])
    else:
        updatefilecontent(query)
        return '', status.HTTP_200_OK


@app.route("/add/", methods=['POST'])
@set_parsers(NQuadsParser)
def addTriple():
    '''
    List or create notes.
    '''
    if request.method == 'POST':
        try:
            data = checkrequest(request)
        except:
            return '', status.HTTP_403_FORBIDDEN

        for graphuri in data['graphs']:
            if not store.graphexists(graphuri):
                print('Graph ' + graphuri + ' nicht da')
                return '', status.HTTP_403_FORBIDDEN

        addtriples(data)
        commitrepo()

        return '', status.HTTP_201_CREATED
    else:
        return '', status.HTTP_403_FORBIDDEN

@app.route("/delete/", methods=['POST', 'GET'])
@set_parsers(NQuadsParser)
def deleteTriple():
    '''
    List or create notes.
    '''
    if request.method == 'POST':
        try:
            values = checkrequest(request)
        except:
            return '', status.HTTP_403_FORBIDDEN

        for graphuri in values['graphs']:
            if not store.graphexists(graphuri):
                print('Graph ' + graphuri + ' nicht da')
                return [note_repr(idx) for idx in sorted(notes.keys())], status.HTTP_403_FORBIDDEN

        deletetriples(values)
        commitrepo()

        return '', status.HTTP_201_CREATED
    else:
        return '', status.HTTP_403_FORBIDDEN

def main():
    app.run(debug=True, use_reloader=False)

if __name__ == '__main__':
    with handleexit.handle_exit(savegraphs):
        objects = initializegraphs()
        store   = objects['store']
        gitrepo = objects['gitrepo']
        main()
