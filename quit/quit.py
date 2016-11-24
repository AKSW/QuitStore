#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')))

import argparse
from quit.core import FileReference, MemoryStore, GitRepo
from quit.conf import QuitConfiguration
from quit.helpers import QueryAnalyzer
from quit.parsers import NQuadsParser
from quit.utils import splitinformation, sparqlresponse
import handleexit
import logging
from flask import request, Response
from flask.ext.api import FlaskAPI, status
from flask.ext.api.decorators import set_parsers
from flask.ext.api.exceptions import NotAcceptable
from flask.ext.cors import CORS
from rdflib import ConjunctiveGraph, Graph, Literal
import json

app = FlaskAPI(__name__)
CORS(app)

werkzeugLogger = logging.getLogger('werkzeug')
werkzeugLogger.setLevel(logging.INFO)

logger = logging.getLogger('core')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('quit.log')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)


def __savefiles():
    """Update the files after a update query was executed on the store."""
    for file in config.getfiles():
        graphs = config.getgraphuriforfile(file)
        content = []
        for graph in graphs:
            content+= store.getgraphcontent(graph)
        fileobject = FileReference(file)
        # TODO: Quick Fix, add sorting to FileReference
        fileobject.setcontent(sorted(content))
        fileobject.savefile()

    return


def __updategit():
    """Private method to add all updated tracked files."""
    gitrepo.addall()
    gitrepo.commit()
    if config.isgarbagecollectionon():
        gitrepo.garbagecollection()

    return


def __removefile(self, graphuri):
    # TODO actions needed to remove file also from
    # - directory and
    # - git repository
    try:
        del self.files[graphuri]
    except:
        return

    try:
        self.store.remove((None, None, None, graphuri))
    except:
        return

    return


def __commit(self, message=None):
    """Private method to commit the changes."""
    try:
        self.gitrepo.commit(message)
    except:
        pass

    return


def reloadstore():
    """Create a new (empty) store and parse all known files into it."""
    store = MemoryStore
    files = config.getfiles()
    for filename in files:
        graphs = config.getgraphuriforfile(filename)
        graphstring = ''
        for graph in graphs:
            graphstring+= str(graph)
        try:
            store.addfile(filename, config.getserializationoffile(filename))
        except:
            pass

    return


def applyupdates(actions):
    """Update files after store was updated."""
    graphsandfiles = config.getgraphurifilemap()
    savefiles = {}

    for entry in actions:
        for action, quad in entry.items():
            if quad[1] != 'default':
                g = quad[1]

                if str(g) in graphsandfiles.keys():
                    s = quad[0][0]
                    p = quad[0][1]
                    o = quad[0][2]

                    isliteral = isinstance(o, Literal)
                    hasnewline = o.n3().endswith('\n')
                    hasmultiquotes = o.n3().startswith('""')

                    if(isliteral and (hasnewline or hasmultiquotes)):
                        line = multilineliteralhack(quad)
                    else:
                        line = s.n3() + ' ' + p.n3() + ' ' + o.n3() + ' ' + g.n3() + ' .'

                    filename = graphsandfiles[str(g)]
                    savefiles[filename] = ''
                    fo = references[filename]

                    if action == 'insert':
                        fo.addquad(line)
                    elif action == 'delete':
                        fo.deletequad(line)
            else:
                pass
                # TODO If default graphs are handled, the updates must be handled here

    # save all files
    for filename in savefiles.keys():
        fo = references[filename]
        fo.sortcontent()
        fo.savefile()

    return


def multilineliteralhack(quad):
    """Handle multi lined literals with N-Quads."""
    temp = Graph()
    temp.add((quad[0][0], quad[0][1], quad[0][2]))
    line = temp.serialize(format='nt').decode('UTF-8')
    line = line.rstrip("\n")
    line = line[:-1] + quad[1].n3() + ' .'

    return line


def initialize(args):
    """Build all needed objects.

    Returns:
        A dictionary containing the store object and git repo object.

    """
    gc = False

    if args.disableversioning:
        logger.info('Versioning is disabled')
        v = False
    else:
        logger.info('Versioning is enabled')
        v = True
        if args.garbagecollection:
            gc = True
            logger.info('Garbage Collection is enabled')

    config = QuitConfiguration(versioning=v, gc=gc)

    logger.debug('Known graphs: ' + str(config.getgraphs()))
    logger.debug('Known files: ' + str(config.getfiles()))
    logger.debug('Path of Gitrepo: ' + str(config.getrepopath()))
    logger.debug('RDF files found in Gitepo:' + str(config.getgraphsfromdir()))

    store = MemoryStore()

    files = config.getfiles()
    gitrepo = GitRepo(config.getrepopath())

    # Load data to store
    for filename in files:
        graphs = config.getgraphuriforfile(filename)
        graphstring = ''
        for graph in graphs:
            graphstring+= str(graph)
        try:
            store.addfile(filename, config.getserializationoffile(filename))
            logger.debug('Success: Graph with URI: ' + graphstring + ' added to my known graphs list')
        except:
            pass

    # Save file objects per file
    filereferences = {}

    for file in config.getfiles():
        graphs = config.getgraphuriforfile(file)
        content = []
        for graph in graphs:
            content+= store.getgraphcontent(graph)
        fileobject = FileReference(file)
        # TODO: Quick Fix, add sorting to FileReference
        fileobject.setcontent(sorted(content))
        filereferences[file] = fileobject

    return {'store': store, 'config': config, 'gitrepo': gitrepo, 'references': filereferences}


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


def processsparql(querystring):
    """Execute a sparql query after analyzing the query string.

    Args:
        querystring: A SPARQL query string.
    Returns:
        SPARQL result set if valid select query.
        None if valid update query.
    Raises:
        Exception: If query is not a valid SPARQL update or select query

    """
    try:
        query = QueryAnalyzer(querystring)
    except NotAcceptable as e:
        print("This is not acceptable:", e)
        exit(1)
    except:
        raise

    if query.getType() == 'SELECT':
        logger.debug('Execute select query')
        result = store.query(query.getParsedQuery())
    elif query.getType() == 'DESCRIBE':
        logger.debug('Skip describe query')
        result = None
    elif query.getType() == 'CONSTRUCT':
        logger.debug('Execute construct query')
        result = store.query(query.getParsedQuery())
    elif query.getType() == 'ASK':
        logger.debug('Execute ask query')
        result = store.query(query.getParsedQuery())
    elif query.getType() == 'UPDATE':
        if query.getParsedQuery() is None:
            query = querystring
        else:
            query = query.getParsedQuery()
        logger.debug('Execute update query')

        if config.isversioningon():
            actions = store.update(query)
            applyupdates(actions)
            __updategit()
            return
        else:
            store.update(query, versioning=False)
            return

    return result


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
        logger.debug('Trying to save graph with URI: ' + graph)
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
        logger.debug('Trying to save graph with URI: ' + graph)
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
    print("Exiting store")
    store.exit()
    print("Store exited")

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
            logger.debug("unknown request method:", request.method)
            return '', status.HTTP_400_BAD_REQUEST
    except:
        logger.debug('Query is missing in request')
        return '', status.HTTP_400_BAD_REQUEST

    try:
        result = processsparql(query)
        pass
    except Exception as e:
        logger.debug('Something is wrong with received query:', e)
        import traceback
        traceback.print_tb(e.__traceback__, limit=20)
        return '', status.HTTP_400_BAD_REQUEST

    # Check weather we have a result (SELECT) or not (UPDATE) and respond correspondingly
    if result is not None:
        return sparqlresponse(result, resultFormat())
    else:
        # resultformat = resultFormat()
        return Response("",
                        content_type=resultFormat()['mime']
                        )
        # return '', status.HTTP_200_OK

@app.route("/git/checkout/", methods=['POST', 'GET'], defaults={'commitid': None})
@app.route('/git/checkout/<string:commitid>')
def checkoutVersion(commitid):
    """Receive a HTTP request with a commit id and initialize store with data from this commit.

    Returns:
        HTTP Response 200: If commit id is valid and store is reinitialized with the data.
        HTTP Response 400: If commit id is not valid.
    """
    if request.method == 'GET':
        if 'commitid' in request.args:
            commitid = request.args['commitid']
    elif request.method == 'POST':
        if 'commitid' in request.form:
            commitid = request.form['commitid']
    if commitid == None:
        msg = 'Commit id is missing in request'
        logger.debug(msg)
        return msg, status.HTTP_400_BAD_REQUEST

    if gitrepo.commitexists(commitid) is True:
        gitrepo.checkout(commitid)
        # TODO store has to be reinitialized with old data
        # Maybe a working copy of quit config, containing file to graph mappings
        # would do the job
        reloadstore()
    else:
        msg = 'Not a valid commit id'
        logger.debug(msg)
        return msg, status.HTTP_400_BAD_REQUEST

    return '', status.HTTP_200_OK


@app.route("/git/log", methods=['GET'])
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
                logger.debug('Graph ' + graphuri + ' is not part of the store')
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
                logger.debug('Graph ' + graphuri + ' is not part of the store')
                return '', status.HTTP_403_FORBIDDEN

        deletetriples(values)

        return '', status.HTTP_201_CREATED
    else:
        return '', status.HTTP_403_FORBIDDEN


@app.route("/pull", methods=['POST', 'GET'])
def pull():
    """Pull from remote.

    Returns:
        HTTP Response 201: If pull was possible
        HTTP Response: 403: If pull did not work
    """
    if store.pull():
        return '', status.HTTP_201_CREATED
    else:
        return '', status.HTTP_403_FORBIDDEN

    return


@app.route("/push", methods=['POST', 'GET'])
def push():
    """Pull from remote.

    Returns:
        HTTP Response 201: If pull was possible
        HTTP Response: 403: If pull did not work
    """
    if store.push():
        return '', status.HTTP_201_CREATED
    else:
        return '', status.HTTP_403_FORBIDDEN

    return


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
    parser = argparse.ArgumentParser()
    parser.add_argument('-nv', '--disableversioning', action='store_true')
    parser.add_argument('-gc', '--garbagecollection', action='store_true')
    args = parser.parse_args()

    objects = initialize(args)
    store = objects['store']
    config = objects['config']
    gitrepo = objects['gitrepo']
    references = objects['references']
    sys.setrecursionlimit(3000)
    # The app is started with an exit handler
    with handleexit.handle_exit(savedexit):
        main()
