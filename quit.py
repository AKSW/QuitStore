from flask import request, url_for
from flask.ext.api import FlaskAPI, status, exceptions
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
    try:
        f = open('config.yml')
        conf = yaml.safe_load(f)
        f.close()
        graphConf = conf['graphs']
    except :
        return False

    store = MemoryStore()

    settings = store.getstoresettings()
    repository = settings['gitrepo']

    versioning = True
    graphs = store.getgraphsfromconf()
    for graphuri, filename in graphs.items():
        print(graphuri, filename)
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
    print('query: ', querystring)
    try:
        query = QueryCheck(querystring)
    except:
        return ('Konnte das Objekt nicht anlegen')
        raise Exception()

    if query.getType() == 'SELECT':
        return store.query(querystring)
    else:
        print('Hier Problem')

    return ('Query is OK')

def checkrequest(request):
    data = []
    graphsInRequest = set()
    for v in request.data.values():
        if not (v['action'] == 'add' or v['action'] == 'delete'):
            return False

        try:
            s = v['s']
            p = v['p']
            o = v['o']
            g = v['g']
        except IndexError:
            print("Missing parameter in JSON")
            return False

        check = [s,p,o,g]

        if '' in check:
            print("Empty value for parameter in JSON")
            return False

        try:
            parse(o, rule='IRI')
            # resource
            o = '<' + o + '>'
        except ValueError:
            # literal
            o = '"' + o + '"'

        try:
            parse(s, rule='IRI')
            parse(p, rule='IRI')
            parse(g, rule='IRI')
            s = '<' + s + '>'
            p = '<' + p + '>'
            graphsInRequest.add(g)
        except ValueError:
            print("Value must be a valid IRI")
            return False

        triple = s + ' ' + p + ' ' + o + ' .'

        try:
            graph = Graph().parse(format='nt',data=triple)
            data.append({'action': v['action'], 'graph': g, 'triple': triple})
        except:
            print('Triple: ' + triple + ' is not valid')
            return False

    return {"graphs": graphsInRequest, "data": data}

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
            addedtriples[data['triple']] = data['graph']
            currentgraph = store.getgraphobject(data['graph'])
            print('Trying to delete: ' + data['triple'])
            currentgraph.deletetriple(data['triple'])
        # collect all triples that should be deleted
        elif data['action'] == 'delete':
            deletetriples[data['triple']] = data['graph']

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

def savegraphs():
    print("Finishing ...")
    for graphuri, filename in store.getgraphs():
        currentgraph = store.getgraphobject(graphuri)
        if not currentgraph.isversioned():
            print("saving a graph ...")
            currentgraph.sortfile()
            currentgraph.savefile()
    print("Bye !!!")

'''
API
'''

@app.route("/", methods=['GET'])
def notes_list():
    '''
    List last commits.
    '''
    # request.method == 'GET'
    return [note_repr(idx) for idx in sorted(notes.keys())]

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
        return [note_repr(idx) for idx in sorted(notes.keys())], status.HTTP_400_BAD_REQUEST

    try:
        result = processsparql(query)
        print('gut')
    except:
        print('Mit der Query stimmt etwas nicht')
        return [note_repr(idx) for idx in sorted(notes.keys())], status.HTTP_400_BAD_REQUEST
    return sparqlresponse(result)

@app.route("/add/", methods=['POST', 'GET'])
def addTriple():
    '''
    List or create notes.
    '''
    if request.method == 'POST':
        print('Post-Request ' + str(request))
        values = checkrequest(request)
        for k, v in values.items():
            print("applychanges : " + k + ':' + str(v) )
        if values == False:
            return [note_repr(idx) for idx in sorted(notes.keys())], status.HTTP_403_FORBIDDEN

        print('Graphliste: ' + str(store.getgraphlist()))
        for graphuri in values['graphs']:
            if not store.graphexists(graphuri):
                print('Graph ' + graphuri + ' nicht da')
                return [note_repr(idx) for idx in sorted(notes.keys())], status.HTTP_403_FORBIDDEN

        idx = max(notes.keys()) + 1

        applychanges(values)

        notes[idx] = values['data']
        return note_repr(idx), status.HTTP_201_CREATED
    else:
        print('Get-Request ' + str(request))
        values = checkrequest(request)

    # request.method == 'GET'
    return [note_repr(idx) for idx in sorted(notes.keys())]

@app.route("/delete/", methods=['POST', 'GET'])
def deleteTriple():
    '''
    List or create notes.
    '''
    if request.method == 'POST':
        values = checkrequest(request)
        idx = max(notes.keys()) + 1
        if not deleteFromGraph(values):
            return '', status.HTTP_204_NO_CONTENT
        notes[idx] = values['triple']
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
    app.run(debug=True)

if __name__ == '__main__':
    with handleexit.handle_exit(savegraphs):
        store = initializegraphs()
        main()
