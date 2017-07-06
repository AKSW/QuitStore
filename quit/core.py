from datetime import datetime
import logging
from os import makedirs
from os.path import abspath, exists, isdir, join
from quit.update import evalUpdate
from pygit2 import GIT_MERGE_ANALYSIS_UP_TO_DATE
from pygit2 import GIT_MERGE_ANALYSIS_FASTFORWARD
from pygit2 import GIT_MERGE_ANALYSIS_NORMAL
from pygit2 import GIT_SORT_REVERSE, GIT_RESET_HARD, GIT_STATUS_CURRENT
from pygit2 import init_repository, clone_repository
from pygit2 import Repository, Signature, RemoteCallbacks, Keypair, UserPass
from rdflib import ConjunctiveGraph, Graph, URIRef, BNode
from subprocess import Popen

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
            filecontentinmem: Boolean to decide if local filesystem should be used to
                or if file content should be kept in memory too . (Defaults false)

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

    def addquads(self, quads):
        """Add quads to the file content."""
        self.content.append(quads)
        self.content = list(set(self.content))
        self.sortcontent()

        return

    def addquad(self, quad):
        """Add a quad to the file content."""
        if(self.quadexists(quad)):
            return

        self.content.append(quad)

        return

    def quadexists(self, quad):
        """Look if a quad is in the file content.

        Returns:
            True if quad was found, False else
        """
        searchPattern = quad

        if searchPattern in self.content:
            return True

        return False

    def deletequads(self, quads):
        """Remove quads from the file content."""
        for quad in quads:
            self.content.remove(quad)

        return True

    def deletequad(self, quad):
        """Remove a quad from the file content."""
        try:
            self.content.remove(quad)
            self.modified = True
        except ValueError:
            # not in list
            pass

        return

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
        data.remove('')

        return data

    def getstoreobject(self):
        """Get the conjunctive graph object.

        Returns:
            graph: A list of strings where each string is a quad.
        """
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

    def update(self, querystring, versioning=True):
        """Execute a SPARQL update query and update the store.

        This method executes a SPARQL update query and updates and commits all affected files.

        Args:
            querystring: A string containing a SPARQL upate query.
        """
        # methods of rdflib ConjunciveGraph
        if versioning:
            actions = evalUpdate(self.store, querystring)
            self.store.update(querystring)
            return actions
        else:
            self.store.update(querystring)
            return

        return

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

    path = ''
    pathspec = []
    repo = None
    callback = None
    author_name = 'QuitStore'
    author_email = 'quit@quit.aksw.org'
    gcProcess = None

    def __init__(self, path, origin=None):
        """Initialize a new repository from an existing directory.

        Args:
            path: A string containing the path to the repository.
        """
        self.logger = logging.getLogger('git_repo.core.quit')
        self.logger.debug('GitRepo, init, Create an instance of GitStore')
        self.path = path

        if not exists(path):
            try:
                makedirs(path)
            except OSError as e:
                raise Exception('Can\'t create path in filesystem:', path, e)

        try:
            self.repo = Repository(path)
        except:
            pass

        if origin:
            self.callback = self.setCallback(origin)

        if self.repo:
            if self.repo.is_bare:
                raise Exception('Bare repositories not supported, yet')

            if origin:
                # set remote
                self.addRemote('origin', origin)
        else:
            if origin:
                # clone
                self.cloneRepository(origin, path, self.callback)
            else:
                self.repo = init_repository(path=path, bare=False)

    def cloneRepository(self, origin, path, callback):
        try:
            repo = clone_repository(
                url=origin,
                path=path,
                bare=False,
                callbacks=callback
            )
            self.addRemote('origin', origin)
            return repo
        except:
            raise Exception('Could not clone from', origin)

    def addall(self):
        """Add all (newly created|changed) files to index."""
        self.repo.index.read()
        self.repo.index.add_all(self.pathspec)
        self.repo.index.write()

    def addfile(self, filename):
        """Add a file to the index.

        Args:
            filename: A string containing the path to the file.
        """
        index = self.repo.index
        index.read()

        try:
            index.add(filename)
            index.write()
        except:
            self.logger.debug('GitRepo, addfile, Couldn\'t add file', filename)

    def addRemote(self, name, url):
        """Add a remote.

        Args:
            name: A string containing the name of the remote.
            url: A string containing the url to the remote.
        """
        try:
            self.repo.remotes.create(name, url)
            self.logger.debug('GitRepo, addRemote, successfully added remote', name, url)
        except:
            self.logger.debug('GitRepo, addRemote, could not add remote', name, url)

        try:
            self.repo.remotes.set_push_url(name, url)
            self.repo.remotes.set_url(name, url)
        except:
            self.logger.debug('GitRepo, addRemote, could not set urls', name, url)

    def checkout(self, commitid):
        """Checkout a commit by a commit id.

        Args:
            commitid: A string cotaining a commitid.
        """
        try:
            commit = self.repo.revparse_single(commitid)
            self.repo.set_head(commit.oid)
            self.repo.reset(commit.oid, GIT_RESET_HARD)
            self.logger.debug('GitRepo, checkout, Checked out commit:', commitid)
        except:
            self.logger.debug('GitRepo, checkout, Commit-ID (' + commitid + ') does not exist')

    def commit(self, message=None):
        """Commit staged files.

        Args:
            message: A string for the commit message.
        Raises:
            Exception: If no files in staging area.
        """
        if self.isstagingareaclean():
            # nothing to commit
            return

        # tree = self.repo.TreeBuilder().write()

        index = self.repo.index
        index.read()
        tree = index.write_tree()

        try:
            author = Signature(self.author_name, self.author_email)
            comitter = Signature(self.author_name, self.author_email)

            if len(self.repo.listall_reference_objects()) == 0:
                # Initial Commit
                if message is None:
                    message = 'Initial Commit from QuitStore'
                self.repo.create_commit('HEAD',
                                        author, comitter, message,
                                        tree,
                                        [])
            else:
                if message is None:
                    message = 'New Commit from QuitStore'
                self.repo.create_commit('HEAD',
                                        author, comitter, message,
                                        tree,
                                        [self.repo.head.get_object().hex]
                                        )
            self.logger.debug('GitRepo, commit, Updates commited')
        except:
            self.logger.debug('GitRepo, commit, Nothing to commit')

    def commitexists(self, commitid):
        """Check if a commit id is part of the repository history.

        Args:
            commitid: String of a Git commit id.
        Returns:
            True, if commitid is part of commit log
            False, else.
        """
        if commitid in self.getids():
            return True
        else:
            return False

    def garbagecollection(self):
        """Start garbage collection.

        Args:
            commitid: A string cotaining a commitid.
        """
        try:
            """
            Check if the garbage collection process is still running
            """
            if self.gcProcess is None or self.gcProcess.poll() is not None:
                """
                Start garbage collection with "--auto" option, which imidietly terminates, if it is not necessary
                """
                self.gcProcess = Popen(["git", "gc", "--auto", "--quiet"])
        except Exception as e:
            self.logger.debug('Git garbage collection failed to spawn', e)
        return

    def getpath(self):
        """Return the path of the git repository.

        Returns:
            A string containing the path to the directory of git repo
        """
        return self.path

    def getcommits(self):
        """Return meta data about exitsting commits.

        Returns:
            A list containing dictionaries with commit meta data
        """
        commits = []
        if len(self.repo.listall_reference_objects()) > 0:
            for commit in self.repo.walk(self.repo.head.target, GIT_SORT_REVERSE):
                # commitdate = datetime.fromtimestamp(float(commit.date)).strftime('%Y-%m-%d %H:%M:%S')
                commits.append({
                    'id': str(commit.oid),
                    'message': str(commit.message),
                    'commit_date': datetime.fromtimestamp(
                        commit.commit_time).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'author_name': commit.author.name,
                    'author_email': commit.author.email,
                    'parents': [c.hex for c in commit.parents],
                    }
                )
        return commits

    def getids(self):
        """Return meta data about exitsting commits.

        Returns:
            A list containing dictionaries with commit meta data
        """
        ids = []
        if len(self.repo.listall_reference_objects()) > 0:
            for commit in self.repo.walk(self.repo.head.target, GIT_SORT_REVERSE):
                ids.append(str(commit.oid))
        return ids

    def isCallbackSet(self):
        """Checks if an authentication callback is already defined in the current GitRepo object.

        Returns:
            True if callback is set, else False
        """
        if self.callback is None:
            return False

        return True

    def isstagingareaclean(self):
        """Check if staging area is clean.

        Returns:
            True, if staginarea is clean
            False, else.
        """
        status = self.repo.status()

        for filepath, flags in status.items():
            if flags != GIT_STATUS_CURRENT:
                return False

        return True

    def pull(self, remote='origin', branch='master'):
        """Pull if possible.

        Return:
            True: If successful.
            False: If merge not possible or no updates from remote.
        """
        try:
            self.repo.remotes[remote].fetch()
        except:
            self.logger.debug('GitRepo, pull,  No remote', remote)

        ref = 'refs/remotes/' + remote + '/' + branch
        remoteid = self.repo.lookup_reference(ref).target
        analysis, _ = self.repo.merge_analysis(remoteid)

        if analysis & GIT_MERGE_ANALYSIS_UP_TO_DATE:
            # Already up-to-date
            pass
        elif analysis & GIT_MERGE_ANALYSIS_FASTFORWARD:
            # fastforward
            self.repo.checkout_tree(self.repo.get(remoteid))
            master_ref = self.repo.lookup_reference('refs/heads/master')
            master_ref.set_target(remoteid)
            self.repo.head.set_target(remoteid)
        elif analysis & GIT_MERGE_ANALYSIS_NORMAL:
            self.repo.merge(remoteid)
            tree = self.repo.index.write_tree()
            msg = 'Merge from ' + remote + ' ' + branch
            author = Signature(self.author_name, self.author_email)
            comitter = Signature(self.author_name, self.author_email)
            self.repo.create_commit('HEAD',
                                    author,
                                    comitter,
                                    msg,
                                    tree,
                                    [self.repo.head.target, remoteid])
            self.repo.state_cleanup()
        else:
            self.logger.debug('GitRepo, pull, Unknown merge analysis result')

    def push(self, remote='origin', branch='master'):
        """Push if possible.

        Return:
            True: If successful.
            False: If diverged or nothing to push.
        """
        ref = ['refs/heads/' + branch]

        try:
            remo = self.repo.remotes[remote]
        except:
            self.logger.debug('GitRepo, push, Remote:', remote, 'does not exist')
            return

        try:
            remo.push(ref, callbacks=self.callback)
        except:
            self.logger.debug('GitRepo, push, Can not push to', remote, 'with ref', ref)

    def getRemotes(self):
        remotes = {}

        try:
            for remote in self.repo.remotes:
                remotes[remote.name] = [remote.url, remote.push_url]
        except:
            return {}

        return remotes

    def setCallback(self, origin):
        """Set a pygit callback for user authentication when acting with remotes.

        This method uses the private-public-keypair of the ssh host configuration.
        The keys are expected to be found at ~/.ssh/
        Warning: Create a keypair that will be used only in QuitStore and do not use
        existing keypairs.

        Args:
            username: The git username (mostly) given in the adress.
            passphrase: The passphrase of the private key.
        """
        from os.path import expanduser
        ssh = join(expanduser('~'), '.ssh')
        pubkey = join(ssh, 'id_quit.pub')
        privkey = join(ssh, 'id_quit')

        from re import search
        # regex to match username in web git adresses
        regex = '(\w+:\/\/)?((.+)@)*([\w\d\.]+)(:[\d]+){0,1}\/*(.*)'
        p = search(regex, origin)
        username = p.group(3)

        passphrase = ''

        try:
            credentials = Keypair(username, pubkey, privkey, passphrase)
        except:
            self.logger.debug('GitRepo, setcallback: Something went wrong with Keypair')
            return

        return RemoteCallbacks(credentials=credentials)
