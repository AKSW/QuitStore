#!/usr/bin/env python3

import git
import logging
from os.path import abspath
from rdflib import ConjunctiveGraph, Graph, URIRef, BNode
from datetime import datetime

corelogger = logging.getLogger('core.quit')

class FileReference:
    """A class that manages n-quad files.

    This class stores inforamtation about the location of a n-quad file and is
    able to add and delete triples/quads to that file.
    """

    def __init__(self, filelocation, versioning=True):
        """Initialize a new FileReference instance.

        Args:
            filelocation: A string of the filepath.
            versioning: Boolean if versioning is enabled or not. (Defaults true)

        Raises:
            ValueError: If no file at the filelocation, or in the given directory + filelocation.
        """
        self.logger = logging.getLogger('file_reference_core.quit')
        self.logger.debug('Create an instance of FileReference')
        self.content = None
        self.path = abspath(filelocation)
        self.modified = False

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

    def getgraphfromfile(self):
        """Return a Conjunctive Graph generated from the referenced file.

        Returns:
            A ConjunctiveGraph
        """
        graph = ConjunctiveGraph()

        try:
            graph.parse(self.path, format='nquads', publicID='http://localhost:5000/')
            self.logger.debug('Success: File', self.path, 'parsed')
            # quadstring = graph.serialize(format="nquads").decode('UTF-8')
            # quadlist = quadstring.splitlines()
            # self.__setcontent(quadlist)
        except:
            # Given file contains non valid rdf data
            # self.logger.debug('Error: File', self.path, 'not parsed')
            # self.__setcontent([[None][None][None][None]])
            pass

        return graph

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

        self.logger.debug('Saving file:', self.path)
        content = self.__getcontent()
        for line in content:
            f.write(line + '\n')
        f.close

        self.logger.debug('File saved')

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


class MemoryStore:
    """A class that combines and syncronieses n-quad files and an in-memory quad store.

    This class contains information about all graphs, their corresponding URIs and
    pathes in the file system. For every Graph (context of Quad-Store) exists a
    FileReference object (n-quad) that enables versioning (with git) and persistence.
    """

    def __init__(self):
        """Initialize a new MemoryStore instance."""
        self.logger = logging.getLogger('memory_store.core.quit')
        self.logger.debug('Create an instance of MemoryStore')
        self.sysconf = Graph()
        self.store = ConjunctiveGraph(identifier='default')
        return

    def getgraphuris(self):
        """Method to get all available named graphs.

        Returns:
            A list containing all graph uris found in store.
        """
        graphs = []
        for graph in self.store.contexts():
            if isinstance(graph, BNode) or str(graph.identifier) == 'default':
                pass
            else:
                graphs.append(graph.identifier)

        return graphs

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

    def graphexists(self, graphuri):
        """Ask if a named graph FileReference object for a named graph URI.

        Args:
            graphuri: A string containing the URI of a named graph

        Returns:
            True or False
        """
        if self.store.get_context(URIRef(graphuri)) is None:
            return False
        else:
            return True

    def addfile(self, filename, serialization):
        """Add a file to the store.

        Args:
            filename: A String for the path to the file.
            serialization: A String containg the RDF format
        Raises:
            ValueError if the given file can't be parsed as nquads.
        """
        try:
            self.store.parse(source=filename, format=serialization)
        except:
            self.logger.debug('Could not import', filename, '.')
            self.logger.debug('Make sure the file exists and contains data in', serialization)
            pass

        return

    def addquads(self, quads):
        """Add quads to the MemoryStore.

        Args:
            quads: Rdflib.quads that should be added to the MemoryStore.
        """
        self.store.addN(quads)
        self.store.commit()

        return

    def query(self, querystring):
        """Execute a SPARQL select query.

        Args:
            querystring: A string containing a SPARQL ask or select query.
        Returns:
            The SPARQL result set
        """
        return self.store.query(querystring)

    def update(self, querystring):
        """Execute a SPARQL update query and update the store.

        This method executes a SPARQL update query and updates and commits all affected files.

        Args:
            querystring: A string containing a SPARQL upate query.
        """
        # methods of rdflib ConjunciveGraph
        self.store.update(querystring)

    def removequads(self, quads):
        """Remove quads from the MemoryStore.

        Args:
            quads: Rdflib.quads that should be removed to the MemoryStore.
        """
        self.store.remove((quads))
        self.store.commit()
        return

    def exit(self):
        """Execute actions on API shutdown."""
        return


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
        self.logger = logging.getLogger('git_repo.core.quit')
        self.logger.debug('Create an instance of GitStore')
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

        try:
            for entry in log:
                # extract timestamp and convert to datetime
                commitdate = datetime.fromtimestamp(float(entry.committed_date)).strftime('%Y-%m-%d %H:%M:%S')
                ids.append(str(entry))
                commits.append({
                    'id': str(entry),
                    'message': str(entry.message),
                    'committeddate': commitdate
                })
        except:
            pass

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
            self.git.add([filename])
        except:
            self.logger.debug('Couldn\'t add file', filename)
            raise

    def addremote(self, name, url):
        """Add a remote.

        Args:
            name: A string containing the name of the remote.
            url: A string containing the url to the remote.
        """
        try:
            self.repo.create_remote(name, url)
            self.logger.debug('Successful added remote', name, url)
        except:
            return False
            self.logger.debug('Could not add remote', name, url)

        return True

    def checkout(self, commitid):
        """Checkout a commit by a commit id.

        Args:
            commitid: A string cotaining a commitid.
        """
        try:
            self.logger.debug('Checked out commit:', commitid)
            self.git.checkout(commitid)
        except:
            self.logger.debug('Commit-ID (' + commitid + ') does not exist')
            return False

        return True

    def commit(self, message=None):
        """Commit staged files.

        Args:
            message: A string for the commit message.
        Raises:
            Exception: If no files in staging area.
        """
        if message is None:
            message = '\"New commit from quit-store\"'

        # TODO Add a meta data
        # committer = str.encode('Quit-Store <quit.store@aksw.org>')
        # commitid = self.repo.do_commit(msg, committer)

        try:
            self.git.commit('-m', message)
            self.__setcommits()
            self.logger.debug('Updates commited')
        except git.exc.GitCommandError:
            self.logger.debug('Nothing to commit')
            return False

        return True

    def commitexists(self, commitid):
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

    def getcommits(self):
        """Return meta data about exitsting commits.

        Returns:
            A list containing dictionaries with commit meta data
        """
        return self.commits

    def isstagingareaclean(self):
        """Check if staging area is clean.

        Returns:
            True, if staginarea is clean
            False, else.
        """
        try:
            self.repo.head.commit.tree
            gitstatus = self.git.diff('HEAD', '--name-only')
        except:
            # A fresh initialized repository
            return False

        if gitstatus == '':
            return True

        return False

    def pull(self, remote='origin', branch='master'):
        """Pull if possible.

        Return:
            True: If successful.
            False: If merge not possible or no updates from remote.
        """
        self.git.fetch(remote, branch)
        idhead = self.git.rev_parse('HEAD')
        idfetchhead = self.git.rev_parse('FETCH_HEAD')
        idbase = self.git.merge_base('HEAD', 'FETCH_HEAD')

        try:
            if idhead == idbase and idhead != idfetchhead:
                pull = self.git.merge('FETCH_HEAD')
                if 'Already up-to-date' not in pull:
                    return True
        except git.exc.GitCommandError:
            pass

        return False

    def push(self, remote='origin', branch='master'):
        """Push if possible.

        Return:
            True: If successful.
            False: If diverged or nothing to push.
        """
        self.git.fetch('--all')
        idhead = self.git.rev_parse('HEAD')
        idfetchhead = self.git.rev_parse('FETCH_HEAD')
        idbase =self.git.merge_base('HEAD', 'FETCH_HEAD')

        try:
            if idhead != idfetchhead and idbase == idfetchhead:
                push = self.git.push('--porcelain', remote, branch)
                if 'error: ' not in push or '[rejected]' not in push:
                    return True
        except git.exc.GitCommandError:
            pass

        return False

    def update(self, push=False):
        """Try to add all updated files.

        Raises:
            Exception: If no tracked file was changed.
        """
        gitstatus = self.git.status('--porcelain')

        if gitstatus == '':
            self.logger.debug('Nothing to add')
            return False

        try:
            self.logger.debug('Staging file(s)')
            self.git.add([''], '-u')
            if push:
                self.git.push()
        except:
            return False

        return True
