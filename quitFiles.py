from flask import Response
from datetime import datetime
from rdflib import ConjunctiveGraph, Graph, URIRef
from rdflib.plugins.sparql import parser
import os
import git


class FileReference:
    """A class that manages n-quad files.

    This class stores inforamtation about the location of a n-quad file and is
    able to add and delete triples/quads to that file.
    """

    directory = '../store/'

    def __init__(self, filelocation, versioning=True):
        """Initialize a new FileReference instance.

        Args:
            filelocation: A string of the filepath.
            versioning: Boolean if versioning is enabled or not. (Defaults true)

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

        if not versioning:
            self.versioning = False
        else:
            try:
                self.repo = git.Repo(self.directory)
                assert not self.repo.bare
            except:
                print(
                    'Error:',
                    self.directory,
                    ' is not a valid Git repository.',
                    'Versioning will fail. Aborting'
                )
                raise

        graph = ConjunctiveGraph()

        try:
            graph.parse(self.path, format='nquads', publicID='http://localhost:5000/')
            print('Success: File', self.path, 'parsed')
        except:
            # Given file contains non valid rdf data
            print('Error: Filei', self.path, 'not parsed')
            raise

        quadstring = graph.serialize(format="nquads").decode('UTF-8')
        quadlist = quadstring.splitlines()
        self.__setcontent(quadlist)
        graph = None

        return

    def reloadcontent(self):
        """Reload the content from file."""
        graph = ConjunctiveGraph()

        try:
            graph.parse(self.path, format='nquads', publicID='http://localhost:5000/')
            print('Success: File', self.path, 'parsed')
            quadstring = graph.serialize(format="nquads").decode('UTF-8')
            quadlist = quadstring.splitlines()
            self.__setcontent(quadlist)
        except:
            # Given file contains non valid rdf data
            print('Error: File', self.path, 'not parsed')
            self.__setcontent([[None][None][None][None]])
            pass

        graph = None

        return

    def __getcontent(self):
        """Return the content of a n-quad file.

        Returns:
            content: A list of strings where each string is a quad.
        """
        return self.content

    def __setcontent(self, content):
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

    def setcontent(self, content):
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

    def addquads(self, quad):
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
            # not in list
            return False

        return True

    def isversioned(self):
        """Check if a File is part of version control system."""
        return(self.versioning)


class GitRepo:
    """A class that manages a git repository.

    This class enables versiong via git for a repository.
    You can stage and commit files and checkout different commits of the repository.
    """

    commits = []
    ids = []

    def __init__(self, path):
        """Initialize a new repository.

        Args:
            path: A string containing the path to the repository.

        Raises:
            Exception if path is not a git repository.
        """
        self.path = path

        try:
            self.repo = git.Repo(self.path)
        except:
            raise

        self.git = self.repo.git
        self.__setcommits()

        return

    def __setcommits(self):
        """Save a list of all git commits, commit messages and dates."""
        commits = []
        ids = []
        log = self.repo.iter_commits('master')

        for entry in log:
            # extract timestamp and convert to datetime
            commitdate = datetime.fromtimestamp(float(entry.committed_date)).strftime('%Y-%m-%d %H:%M:%S')
            ids.append(str(entry))
            commits.append({
                'id': str(entry),
                'message': str(entry.message),
                'committeddate': commitdate
            })

        self.commits = commits
        self.ids = ids

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

    def getcommits(self):
        """Return meta data about exitsting commits.

        Returns:
            A list containing dictionaries with commit meta data
        """
        return self.commits

    def checkout(self, commitid):
        """Checkout a commit by a commit id.

        Args:
            commitid: A string cotaining a commitid.
        """
        print('Trying to checkout', commitid)
        self.git.checkout(commitid)
        try:
            self.git.checkout(commitid)
        except:
            raise Exception()

        return

    def commitexist(self, commitid):
        """Check if a commit id is part of the repository history.

        Args:
            commitid: String of a Git commit id.
        Returns:
            True, if commitid is part of commit log
            False, else.
        """
        if commitid in self.ids:
            return True
        else:
            return False

    def update(self):
        """Trie to add all updated files.

        Raises:
            Exception: If no tracked file was changed.
        """
        gitstatus = self.git.status('--porcelain')

        if gitstatus == '':
            print('Nothing to add')
            return

        try:
            print("Staging file(s)")
            self.git.add([''], '-u')
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

        if message is None:
            message = '\"New commit from quit-store\"'

        # TODO Add a meta data
        # committer = str.encode('Quit-Store <quit.store@aksw.org>')
        # commitid = self.repo.do_commit(msg, committer)

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

    path = None

    def __init__(self):
        """Initialize a new MemoryStore instance."""
        self.sysconf = Graph()
        self.sysconf.parse('config.ttl', format='turtle')
        self.store = ConjunctiveGraph(identifier='default')
        self.path = self.getstorepath()
        self.repo = GitRepo(self.path)
        self.files = {}
        return

    def __reinit(self):
        """Renitialize the ConjunctiveGraph."""
        self.store = ConjunctiveGraph(identifier='default')

        for graphuri in self.getgraphuris():
            filereference = self.getgraphobject(graphuri)
            filereference.reloadcontent()
            content = filereference.getcontent()
            data = '\n'.join(content)

            try:
                self.store.parse(data=data, format='nquads')
            except:
                print('Something went wrong with file for graph: ', graphuri)
                self.store.__removefile(graphuri)
                pass

        return

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
        """Private method to add all updated tracked files."""
        self.repo.update()

        return

    def __removefile(self, graphuri):
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
        self.repo.commit(message)

        return

    def getgraphs(self):
        """Method to get all available (public) named graphs.

        Returns:
            A dictionary of graphuri:FileReference tuples.
        """
        return self.files.items()

    def storeisvalid(self):
        """Check if the given MemoryStore is valid.

        Returns:
            True if, Fals if not.
        """
        graphsfromconf = list(self.getgraphsfromconf().values())
        graphsfromdir = self.getgraphsfromdir()

        for filename in graphsfromconf:
            if filename not in graphsfromdir:
                return False
            else:
                print('File found')
        return True

    def getgraphuris(self):
        """Return all URIs of named graphs.

        Returns:
            A dictionary containing all URIs of named graphs.
        """
        return self.files.keys()

    def getgraphobject(self, graphuri):
        """Return the FileReference object for a named graph URI.

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
        """Add a file to the store.

        This method looks if file is already part of repo.
        If not, test if given path exists, is file, is valid.
        If so, import into grahp and edit triple to right path if needed.

        Args:
            graphuri: The URI of a named graph.
            FileReferenceObject: The FileReference instance linking the quad file.
        Raises:
            ValueError if the given file can't be parsed as nquads.
        """
        self.files[graphuri] = FileReferenceObject
        content = FileReferenceObject.getcontent()
        data = '\n'.join(content)
        try:
            self.store.parse(data=data, format='nquads')
        except:
            print('Something went wrong with file: ' + self.file)
            raise ValueError

        return

    def getconfforgraph(self, graphuri):
        """Get the configuration for a named graph.

        This method returns configuration parameters (e.g. path to file) for a named graph.

        Args:
            graphuri: The URI if a named graph.
        Returns:
            A dictionary of configuration parameters and their values.
        """
        nsQuit = 'http://quit.aksw.org'
        query = 'SELECT ?graphuri ?filename WHERE { '
        query+= '  <' + graphuri + '> <' + nsQuit + '/Graph> . '
        query+= '  ?graph <' + nsQuit + '/graphUri> ?graphuri . '
        query+= '  ?graph <' + nsQuit + '/hasQuadFile> ?filename . '
        query+= '}'
        result = self.sysconf.query(query)

        values = {}

        for row in result:
            values[str(row['graphuri'])] = str(row['filename'])

        return values

    def getgraphsfromconf(self):
        """Get all URIs of graphs that are configured in config.ttl.

        This method returns all graphs and their corroesponding quad files.

        Returns:
            A dictionary of URIs of named graphs their quad files.
        """
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

        return values

    def getgraphsfromdir(self):
        """Get the files that are part of the repository (tracked or not).

        Returns:
            A list of filepathes.
        """
        path = self.path
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        return files

    def getstoresettings(self):
        """Get the path of Git repository from configuration.

        Returns:
            A list of all repositories given in configuration.
        """
        nsQuit = 'http://quit.aksw.org'
        query = 'SELECT ?gitrepo WHERE { '
        query+= '  <http://my.quit.conf/store> <' + nsQuit + '/pathOfGitRepo> ?gitrepo . '
        query+= '}'
        result = self.sysconf.query(query)
        settings = {}
        for value in result:
            settings['gitrepo'] = value['gitrepo']

        return settings

    def getstorepath(self):
        """Return the path of the repository.

        Returns:
            A string containing the path of git repository.
        """
        if self.path is None:
            nsQuit = 'http://quit.aksw.org'
            query = 'SELECT ?gitrepo WHERE { '
            query+= '  <http://my.quit.conf/store> <' + nsQuit + '/pathOfGitRepo> ?gitrepo . '
            query+= '}'
            result = self.sysconf.query(query)
            for value in result:
                self.directory = value['gitrepo']

        return self.directory

    def processsparql(self, querystring):
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
            query = QueryCheck(querystring)
        except:
            raise Exception()

        if query.getType() == 'SELECT':
            print('Execute select query')
            result = self.__query(querystring)
            print('SELECT result', result)
        else:
            print('Execute update query')
            result = self.__update(querystring)

        return result

    def __query(self, querystring):
        """Execute a SPARQL select query.

        Args:
            querystring: A string containing a SPARQL ask or select query.
        Returns:
            The SPARQL result set
        """
        return self.store.query(querystring)

    def __update(self, querystring):
        """Execute a SPARQL update query and update the store.

        This method executes a SPARQL update query and updates and commits all affected files.

        Args:
            querystring: A string containing a SPARQL upate query.
        """
        # methods of rdflib ConjunciveGraph
        self.store.update(querystring)
        self.store.commit()
        # methods of MemoryStore to update the file system and git
        self.__updatecontentandsave()
        self.__updategit()
        self.__commit(querystring)

        return

    def addquads(self, quads):
        """Add quads to the MemoryStore.

        Args:
            quads: Rdflib.quads that should be added to the MemoryStore.
        """
        self.store.addN(quads)
        self.store.commit()

        return

    def removequads(self, quads):
        """Remove quads from the MemoryStore.

        Args:
            quads: Rdflib.quads that should be removed to the MemoryStore.
        """
        self.store.remove((quads))
        self.store.commit()
        return

    def reinitgraph(self, graphuri):
        """Reset named graph.

        Args:
            graphuri: The URI of a named graph.
        """
        self.store.remove((None, None, None, graphuri))

        for k, v in self.files.items():
            if k == graphuri:
                FileReferenceObject = v
                break

        try:
            content = FileReferenceObject.getcontent()
            self.store.parse(data=''.join(content), format='nquads')
        except:
            print('Something went wrong with file:', self.filepath)
            raise ValueError

        return

    def getgraphcontent(self, graphuri):
        """Get the serialized content of a named graph.

        Args:
            graphuri: The URI of a named graph.
        Returns:
            content: A list of strings where each string is a quad.
        """
        data = []
        context = self.store.get_context(URIRef(graphuri))
        triplestring = context.serialize(format='nt').decode('UTF-8')

        # Since we have triples here, we transform them to quads by adding the graphuri
        # TODO This might cause problems if ' .\n' will be part of a literal.
        #   Maybe a regex would be a better solution
        triplestring = triplestring.replace(' .\n', ' <' + graphuri + '> .\n')

        data = triplestring.splitlines()

        return data

    def getcommits(self):
        """Return meta data about exitsting commits.

        Returns:
            A list containing dictionaries with commit meta data
        """
        return self.repo.getcommits()

    def checkout(self, commitid):
        """Checkout a commit by a commit id.

        Args:
            commitid: A string cotaining a commitid.
        """
        self.repo.checkout(commitid)
        self.__reinit()
        return

    def commitexists(self, commitid):
        """Check if a commit id is part of the repository history.

        Args:
            commitid: String of a Git commit id.
        Returns:
            True, if commitid is part of commit log
            False, else.
        """
        return self.repo.commitexist(commitid)

    def exit(self):
        """Execute actions on API shutdown."""
        return


class QueryCheck:
    """A class that provides methods for received sparql query strings.

    This class is used to classify a given query string.
    At the moment the class distinguishes between SPARQL Update and Select queries.
    """

    def __init__(self, querystring):
        """Initialize a check for a given query string.

        Args:
            querystring: A string containing a query.
        """
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
        """Return the type of a query.

        Returns:
            A string containing the query type.
        """
        return self.queryType

    def getParsedQuery(self):
        """Return the query object (rdflib) of a query string.

        Returns:
            The query object after a query string was parsed with Rdflib.
        """
        return self.parsedQuery


def sparqlresponse(result):
    """Create a FLASK HTTP response for sparql-result+json."""
    return Response(
            result.serialize(format='json').decode('utf-8'),
            content_type='application/sparql-results+json'
            )


def splitinformation(quads, GraphObject):
    """Split quads ."""
    data = []
    graphsInRequest = set()
    for quad in quads:
        graph = quad[3].n3().strip('[]')
        if graph.startswith('_:', 0, 2):
            graphsInRequest.add('default')
            data.append({
                        'graph': 'default',
                        'quad': quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' .\n'
                        })
        else:
            graphsInRequest.add(graph.strip('<>'))
            data.append({
                        'graph': graph.strip('<>'),
                        'quad': quad[0].n3() + ' ' + quad[1].n3() + ' ' + quad[2].n3() + ' ' + graph + ' .\n'
                        })
    return {'graphs': graphsInRequest, 'data': data, 'GraphObject': GraphObject}
