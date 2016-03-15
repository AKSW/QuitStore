from flask import Response
from rdflib import ConjunctiveGraph, Graph
from rdflib.plugins.sparql import parser
from rfc3987 import parse
import os
import sys
import git
from dulwich.repo import Repo
import pdb

'''
This class stores inforamtation about the location of a n-quad file and is able
to add and delete triples/quads to that file. Optionally it enables versioning
via git
'''
class FileReference:

    directory = '../store/'
    directory = '/home/norman/Documents/Arbeit/LEDS/ASPA/Scripts/store/'

    def __init__(self, filelocation, versioning):
        self.content = None
        self.modified = False
        self.versioning = True

        # Try to open file and set the new path if file was not part of the git store, yet
        if os.path.isfile(os.path.join(self.directory, filelocation)):
            self.path = os.path.join(self.directory, filelocation)
            self.filename = filelocation
        elif os.path.isfile(filelocation):
            # File is read the first time
            filename = os.path.split(filelocation)
            # Set path to
            self.path = os.path.join(self.directory, filename[1])
            self.filename = filename[1]
        else:
            raise ValueError


        if versioning == False:
            self.versioning = False
        else:
            try:
                self.repo = git.Repo(self.directory)
                assert not self.repo.bare
            except:
                print('Error: ' + self.directory + ' is not a valid git repository. Versioning will fail. Aborting')
                raise

        graph = ConjunctiveGraph()


        try:
            print('Success: File parsed')
            graph.parse(self.path, format='nquads', publicID='http://localhost:5000/')
        except:
            # Given file contains non valid rdf data
            print('Error: File not parsed')
            raise

        quads = graph.quads()
        self.__setcontent(self.__serializequads(quads))
        graph = None

        return

    def __getcontent(self):
        return self.content

    def __setcontent(self, content):
        self.content = content
        return

    def __serializequads(self, quads):
        data = []
        for quad in quads:
            graph = quad[3].n3().strip('[]')
            if graph.startswith('_:', 0, 2):
                data.append(quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' .\n')
            else:
                data.append(quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' ' + graph + ' .\n')
        return data

    def savefile(self):
        #if self.modified == False:
        #    return

        f = open(self.path, "w")

        for line in self.content:
            f.write(line)
        f.close

        print('File saved')

    def sortfile(self):
        try:
            self.content = sorted(self.content)
        except AttributeError:
            pass

    def commit(self):
        if self.versioning == False or self.modified == False:
            return

        gitstatus = self.repo.git.status('--porcelain')

        if gitstatus == '':
            self.modified = False
            return

        try:
            print("Trying to stage " + self.filename)
            self.repo.index.add([self.filename])
        except:
            print('Couldn\'t stage file: ' + self.filename)
            raise

        msg = '\"New commit from quit-store\"'
        committer = str.encode('Quit-Store <quit.store@aksw.org>')
        #commitid = self.repo.do_commit(msg, committer)

        try:
            print("Trying to commit " + self.filename)
            self.repo.git.commit('-m', msg)
        except:
            print('Couldn\'t commit file: ' + self.path)
            raise

        self.modified == False

    def addtriple(self, quad, resort = True):
        print('Trying to add: ' + quad)
        self.content.append(quad + '\n')
        self.modified = True

    def searchtriple(self, triple):
        searchPattern = triple + '\n'

        if searchPattern in self.content:
            return True

        return False

    def deletetriple(self, quad):
        searchPattern = quad + '\n'
        try:
            self.content.remove(searchPattern)
            self.modified = True
        except ValueError:
            #not in list
            return False

        return True

    def getcontent(self):
        return(self.content)

    def setcontent(self, content):
        self.content = content

    def isversioned(self):
        return(self.versioning)

class GitRepo:
    def __init__(self, path):
        self.path = path

'''
This class contains information about all Graphs, their corresponding URIs and
pathes in the file system. To every Graph (context of Quad-Store) exists a
FileReference object (n-quad) that enables versioning (with git) and persistence.
'''
class MemoryStore:
    def __init__(self):
        self.path = '../store'
        self.sysconf = Graph()
        self.sysconf.parse('config.ttl', format='turtle')
        self.store = ConjunctiveGraph(identifier='default')
        self.files = {}
        return

    def getgraphs(self):
        return self.files.items()

    def storeisvalid(self):
        graphsfromconf = list(self.getgraphsfromconf().values())
        graphsfromdir  = self.getgraphsfromdir()
        for filename in graphsfromconf:
            if filename not in graphsfromdir:
                return False
            else:
                print('File found')
        return True

    def getgraphobject(self, graphuri):
        for k, v in self.files.items():
            if k == graphuri:
                return v
        return

    def graphexists(self, graphuri):
        graphuris = list(self.files.keys())
        try:
            graphuris.index(graphuri)
            return True
        except ValueError:
            return False

    def addFile(self, graphuri, FileReferenceObject):
        # look if file is already part of repo
        # if not, test if given path exists, is file, is valid
        # if so, import into grahp and edit triple to right path if needed

        self.files[graphuri] = FileReferenceObject
        try:
            content = FileReferenceObject.getcontent()
            self.store.parse(data=''.join(content), format='nquads')
        except:
            print('Something went wrong with file: ' + name)
            raise ValueError

    def getconfforgraph(self, graphuri):
        nsQuit = 'http://quit.aksw.org'
        query = 'SELECT ?graphuri ?filename WHERE { '
        query+= '  <' + graphuri + '> <' + nsQuit + '/Graph> . '
        query+= '  ?graph <' + nsQuit + '/graphUri> ?graphuri . '
        query+= '  ?graph <' + nsQuit + '/hasQuadFile> ?filename . '
        query+= '}'
        result = self.sysconf.query(query)

        for row in result:
            values[str(row['graphuri'])] = str(row['filename'])
        #return list(self.files.keys())
        return values


    def getgraphsfromconf(self):
        nsQuit = 'http://quit.aksw.org'
        query = 'SELECT DISTINCT ?graphuri ?filename WHERE { '
        query+= '  ?graph a <' + nsQuit + '/Graph> . '
        query+= '  ?graph <' + nsQuit + '/graphUri> ?graphuri . '
        query+= '  ?graph <' + nsQuit + '/hasQuadFile> ?filename . '
        query+= '}'
        result = self.sysconf.query(query)
        values = {}
        for row in result:
            values[str(row['graphuri'])] = str(row['filename'])
        #return list(self.files.keys())
        return values

    def getgraphsfromdir(self):
        path = self.path
        files = [ f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        return files

    def getstoresettings(self):
        nsQuit = 'http://quit.aksw.org'
        query = 'SELECT ?gitrepo WHERE { '
        query+= '  <http://my.quit.conf/store> <' + nsQuit + '/pathOfGitRepo> ?gitrepo . '
        query+= '}'
        result = self.sysconf.query(query)
        settings = {}
        for value in result:
            settings['gitrepo'] = value['gitrepo']
        #return list(self.files.keys())
        return settings

    def query(self, querystring):
        return self.store.query(querystring)

    def update(self, querystring):
        return self.store.update(querystring)

    def getgraphcontent(self, graphuri):
        try:
            quads = self.store.quads((None, None, None, graphuri))
        except:
            raise

        data = []
        for quad in quads:
            graph = quad[3].n3().strip('[]')
            if graph.startswith('_:', 0, 2):
                data.append(quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' .\n')
            else:
                data.append(quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' ' + graph + ' .\n')
        return data


class QueryCheck:
    def __init__(self, querystring):
        self.query = querystring
        self.parsedQuery = None
        self.queryType = None

        try:
            self.parsedQuery = parser.parseQuery(querystring)
            self.queryType = 'SELECT'
            return
        except:
            pass

        try:
            self.parsedQuery = parser.parseUpdate(querystring)
            self.queryType = 'UPDATE'
            return
        except:
            pass

        raise Exception

    def getType(self):
        return self.queryType

    '''
    This method checks the given SPARQL query. All Select Queries will return
    an empty diff.
    Queries containing the keywords 'insert' or 'delete' may return a diff.
    To generate the diffs each occurence of 'insert' or 'delete' will be
    rewritten into a construct query.
    '''
    def getParsedQuery(self):
        return self.parsedQuery

    def getResult(self):
        return

    def getdiff(self):
        try:
            delstart = self.query.find('DELETE')
        except:
            # no DELETE part
            pass

        try:
            insstart = self.query.find('INSERT')
        except:
            # no INSERT part
            pass

        try:
            insstart = self.query.find('INSERT')
        except:
            # no DELETE part
            pass

        return

    def getquery(self):
        return self.query

    def __isvalidquery(self):
        query = str(request.args.get('query'))
        return

    def __parse(self):
        return

def sparqlresponse(result):
    return Response(
            result.serialize(format='json').decode('utf-8'),
            content_type='application/sparql-results+json'
            )

def splitinformation(quads):
    data = []
    graphsInRequest = set()
    for quad in quads:
        graph = quad[3].n3().strip('[]')
        if graph.startswith('_:', 0, 2):
            graphsInRequest.add('default')
            data.append({
                        'graph': 'default',
                        'quad' : quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' .\n'
                        })
        else:
            graphsInRequest.add(graph)
            data.append({
                        'graph': graph,
                        'quad' : quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' ' + graph + ' .\n'
                        })
    return {'graphs':graphsInRequest, 'data':data}
