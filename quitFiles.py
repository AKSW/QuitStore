from flask import Response
from datetime import datetime
from rdflib import ConjunctiveGraph, Graph, URIRef
from rdflib.plugins.sparql import parser
from rfc3987 import parse
import os
import sys
import git
import pdb

class FileReference:
    """A class that manages n-quad files.

    This class stores inforamtation about the location of a n-quad file and is able
    to add and delete triples/quads to that file.
    """

    directory = '/home/norman/Documents/Arbeit/LEDS/ASPA/Scripts/store/'

    def __init__(self, filelocation, versioning=True):
        """Initialize a new FileReference instance.

        Args:
            filelocation: A string of the filepath.
            versioning: Boolean if versioning is enabled or not. Default is true == enabled.

        Raises:
            ValueError: If no file at the filelocation, or in the given directory + filelocation.
        """
        self.content = None
        self.modified = False

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
            graph.parse(self.path, format='nquads', publicID='http://localhost:5000/')
            print('Success: File',self.path,'parsed')
        except:
            # Given file contains non valid rdf data
            print('Error: Filei', self.path, 'not parsed')
            raise

        quadstring = graph.serialize(format="nquads").decode('UTF-8')
        quadlist = quadstring.splitlines()
        self.__setcontent(quadlist)
        graph = None

        return

    def __getcontent(self):
        """Return the content of a n-quad file.
        Returns:
            content: A list of strings where each string is a quad.
        """
        return self.content

    def __setcontent(self, content: list):
        """Set the content of a n-quad file.
        Args:
            content: A list of strings where each string is a quad.
        """
        self.content = content
        return

    def getcontent(self):
        """Public method that returns the content of a nquad file.
        Returns:
            content: A list of strings where each string is a quad.
        """
        return self.__getcontent()

    def setcontent(self, content: list):
        """Public method to set the content of a n-quad file.
        Args:
            content: A list of strings where each string is a quad.
        """
        self.__setcontent(content)
        return

    def savefile(self):
        """Save the file."""
        f = open(self.path, "w")

        content = self.__getcontent()
        for line in content:
            f.write(line + '\n')
        f.close

        print('File saved')

    def sortcontent(self):
        """Order file content."""
        content = self.__getcontent()

        try:
            self.__setcontent(sorted(content))
        except AttributeError:
            pass

    def addquads(self, quad, sort = True):
        """Add quads to the file content."""
        self.content.append(quad)
        self.sortcontent()

        return

    def searchquad(self, quad):
        """Look if a quad is in the file content.
        Returns:
            True if quad was found, False else
        """
        searchPattern = quad + '\n'

        if searchPattern in self.content:
            return True

        return False

    def deletequad(self, quad):
        """Add quads to the file content."""
        searchPattern = quad
        try:
            self.content.remove(searchPattern)
            self.modified = True
        except ValueError:
            #not in list
            return False

        return True

    def isversioned(self):
        return(self.versioning)

class GitRepo:
    """A class that manages a git repository

    This class enables versiong via git for a repository.
    You can stage and commit files and checkout different commits of the repository.
    """
    commits = []

    def __init__(self, path):
        """Initialize a new repository.

        Args:
            path: A string containing the path to the repository.

        Raises:
            Exception if path is not a git repository.
        """
        self.path    = path
        try:
            self.repo    = git.Repo(self.path)
        except:
            raise
        self.git     = self.repo.git
        self.__setcommits()

        return

    def addfile(self, filename):
        """Add a file that should be tracked.

        Args:
            filename: A string containing the path to the file.
        Raises:
            Exception: If file was not found under 'filename' or if file is part of store.
        """
        gitstatus = self.git.status('--porcelain')

        if gitstatus == '':
            self.modified = False
            return

        try:
            print("Trying to stage file", filename)
            self.git.add([filename])
        except:
            print('Couldn\'t stage file', filename)
            raise


    def __setcommits(self):
        """Save a list of all git commits, commit messages and dates. """
        commits = []
        log = self.repo.iter_commits('master')

        for entry in log:
            # extract timestamp and convert to datetime
            commitdate = datetime.fromtimestamp(float(entry.committed_date)).strftime('%Y-%m-%d %H:%M:%S')
            commits.append({
                'id':str(entry),
                'message':str(entry.message),
                'committeddate':commitdate
            })

        self.commits = commits
        return

    def getcommits(self):
        """Return meta data about exitsting commits.

        Returns:
            A list containing dictionaries with commit meta data
        """
        return self.commits

    def update(self):
        """Tries to add all updated files.

        Raises:
            Exception: If no tracked file was changed.
        """
        gitstatus = self.git.status('--porcelain')

        if gitstatus == '':
            print('Nothing to add')
            return

        try:
            print("Staging file(s)")
            self.git.add([''],'-u')
        except:
            raise

        return

    def commit(self, message=None):
        """Commit staged files.

        Args:
            message: A string for the commit message.
        Raises:
            Exception: If no files in staging area.
        """
        gitstatus = self.git.status('--porcelain')

        if gitstatus == '':
            print('Nothing to commit')
            return

        if message == None:
            message = '\"New commit from quit-store\"'

        committer = str.encode('Quit-Store <quit.store@aksw.org>')
        #commitid = self.repo.do_commit(msg, committer)

        try:
            print('Commit updates')
            self.git.commit('-m', message)
            self.__setcommits()
        except git.exc.GitCommandError:
            raise

        return


class MemoryStore:
    """
    A class that combines and syncronieses n-quad files and an in-memory quad store.

    This class contains information about all graphs, their corresponding URIs and
    pathes in the file system. For every Graph (context of Quad-Store) exists a
    FileReference object (n-quad) that enables versioning (with git) and persistence.
    """
    def __init__(self):
        """Initialize a new MemoryStore instance."""
        self.path = '/home/norman/Documents/Arbeit/LEDS/ASPA/Scripts/store/'
        self.sysconf = Graph()
        self.sysconf.parse('config.ttl', format='turtle')
        self.store = ConjunctiveGraph(identifier='default')
        self.repo = GitRepo(self.path)
        self.files = {}
        return

    def exit(self):
        """This method can be used to proceed actions on API shutdown."""
        pass

    def __updatecontentandsave(self):
        """Update the files after a update query was executed on the store and save."""
        for graphuri, fileobject in self.getgraphs():
            content = self.getgraphcontent(graphuri)
            fileobject.setcontent(content)
            fileobject.savefile()

        return

    def __savefiles(self):
        """Update the files after a update query was executed on the store."""
        for graphuri, fileobject in self.getgraphs():
            if fileobject.isversioned():
                fileobject.savefile()

        return

    def __updategit(self):
        self.repo.update()

        return

    def __commit(self, message=None):
        self.repo.commit(message)

        return

    def getgraphs(self):
        """Method to get all available (public) named graphs.

        Returns:
            A dictionary of graphuri:FileReference tuples.
        """
        return self.files.items()

    def storeisvalid(self):
        """This method checks if the given MemoryStore is valid.

        Returns:
            True if, Fals if not.
        """
        graphsfromconf = list(self.getgraphsfromconf().values())
        graphsfromdir  = self.getgraphsfromdir()
        for filename in graphsfromconf:
            if filename not in graphsfromdir:
                return False
            else:
                print('File found')
        return True

    def getgraphobject(self, graphuri):
        """This method returns the FileReference object for a named graph URI.

        Args:
            graphuri: A string containing the URI of a named graph

        Returns:
            The FileReference object if graphuri is a named graph of MemoryStore.
            None if graphuri is not a named graph of MemoryStore.
        """
        for k, v in self.files.items():
            if k == graphuri:
                return v
        return

    def graphexists(self, graphuri):
        """Ask if a named graph FileReference object for a named graph URI.

        Args:
            graphuri: A string containing the URI of a named graph

        Returns:
            The FileReference object if graphuri is a named graph of MemoryStore.
            None if graphuri is not a named graph of MemoryStore.
        """
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
        content = FileReferenceObject.getcontent()
        data = '\n'.join(content)
        try:
            self.store.parse(data=data, format='nquads')
        except:
            print('Something went wrong with file: ' + self.file)
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

    def getstorepath(self):
        return self.path

    def processsparql(self, querystring):
        """This method takes a string containing a SPARQL query and executes it.

        Args:
            querystring: A SPARQL query string.
        Returns:
            SPARQL result set if valid select query.
            None if valid update query.
        Raises:
            Exception: If query is not a valid SPARQL update or select query

        """

        #try:
        query = QueryCheck(querystring)
        #except:
        #    raise Exception()

        if query.getType() == 'SELECT':
            print('Execute select query')
            result = self.__query(querystring)
            print('SELECT result', result)
        else:
            print('Execute update query')
            result = self.__update(querystring)

        return result

    def __query(self, querystring):
        return self.store.query(querystring)

    def __update(self, querystring):
        self.store.update(querystring)
        self.store.commit()
        self.__updatecontentandsave()
        self.__updategit()
        self.__commit(querystring)
        return

    def addquads(self, quads):
        self.store.addN(quads)
        self.store.commit()
        return

    def removequads(self, quads):
        self.store.remove((quads))
        self.store.commit()
        return

    def reinitgraph(self, graphuri):
        self.store.remove((None, None, None, graphuri))
        for k, v in self.files.items():
            if k == graphuri:
                FileReferenceObject = v
                break
        content = FileReferenceObject.getcontent()
        self.store.parse(data=''.join(content), format='nquads')
        try:
            #content = FileReferenceObject.getcontent()
            pass
            #self.store.parse(data=''.join(content), format='nquads')
        except:
            print('Something went wrong with file:', self.filepath)
            raise ValueError

        return

    def getgraphcontent(self, graphuri):
        data = []
        context = self.store.get_context(URIRef(graphuri))

        triplestring = context.serialize(format='nt').decode('UTF-8')

        # Since we have triples here, we transform them to quads by adding the graphuri
        # TODO This might cause problems if ' .\n' will be part of a literal.
        #   Maybe a regex would be a better solution
        triplestring = triplestring.replace(' .\n', ' <' + graphuri + '> .\n')

        data = triplestring.splitlines()

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

def splitinformation(quads, GraphObject):
    data = []
    graphsInRequest = set()
    for quad in quads:
        graph = quad[3].n3().strip('[]')
        if graph.startswith('_:', 0, 2):
            graphsInRequest.add('default')
            data.append({
                        'graph'  : 'default',
                        'quad'   : quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' .\n'
                        })
        else:
            graphsInRequest.add(graph.strip('<>'))
            data.append({
                        'graph'  : graph.strip('<>'),
                        'quad'   : quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' ' + graph + ' .\n'
                        })
    return {'graphs':graphsInRequest, 'data':data, 'GraphObject':GraphObject}
