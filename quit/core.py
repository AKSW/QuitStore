from datetime import datetime
import logging
from os import makedirs, environ
from os.path import abspath, exists, isdir, isfile, join, expanduser
from quit.exceptions import QuitGitRepoError
from quit.update import evalUpdate
from pygit2 import GIT_MERGE_ANALYSIS_UP_TO_DATE
from pygit2 import GIT_MERGE_ANALYSIS_FASTFORWARD
from pygit2 import GIT_MERGE_ANALYSIS_NORMAL
from pygit2 import GIT_SORT_REVERSE, GIT_RESET_HARD, GIT_STATUS_CURRENT
from pygit2 import init_repository, clone_repository
from pygit2 import Repository, Signature, RemoteCallbacks
from pygit2 import KeypairFromAgent, Keypair, UserPass
from pygit2 import credentials
from rdflib import ConjunctiveGraph, Graph, URIRef, BNode
from subprocess import Popen

logger = logging.getLogger('quit.core')


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
        logger = logging.getLogger('quit.core.FileReference')
        logger.debug('Create an instance of FileReference')
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
            logger.debug('Success: File', self.path, 'parsed')
        except KeyError as e:
            # Given file contains non valid rdf data
            # logger.debug('Error: File', self.path, 'not parsed')
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

        logger.debug('Saving file:', self.path)
        content = self.__getcontent()
        for line in content:
            f.write(line + '\n')
        f.close

        logger.debug('File saved')

    def sortcontent(self):
        """Order file content."""
        content = self.__getcontent()

        try:
            self.__setcontent(sorted(set(content)))
        except AttributeError:
            pass

    def addquads(self, quads):
        """Add quads to the file content."""
        self.content.append(quads)
        self.sortcontent()

        return

    def addquad(self, quad):
        """Add a quad to the file content."""

        self.content.append(quad)

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
        logger = logging.getLogger('quit.core.MemoryStore')
        logger.debug('Create an instance of MemoryStore')
        self.store = ConjunctiveGraph(identifier='default')
        self.blanknodessupport = False
        self.atomicgraphs = {}

    def getAtomicGraphs(self):
        return self.atomicgraphs

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
        except Exception as e:
            logger.debug(e)
            logger.debug(
                "Could not import file: {}. " +
                "Make sure the file exists and contains data in  {}".format(
                    filename,
                    serialization
                )
            )

    def addquads(self, quads):
        """Add quads to the MemoryStore.

        Args:
            quads: Rdflib.quads that should be added to the MemoryStore.
        """
        self.store.addN(quads)
        self.store.commit()

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

    def setAtomicGraphs(self):
        """Set all atomic graphs per named graph."""
        self.blanknodessupport = True
        for graph in self.getgraphuris():
            self.atomicgraphs[graph.n3()] = {}
            bnodes = []
            context = self.store.get_context(graph)
            for s, p, o in context.triples((None, None, None)):
                bnfound = False
                if isinstance(s, BNode) and s.n3() not in bnodes:
                    bnfound = True
                    bnodes.append(s.n3())
                    agraph = AtomicGraph(s, context)
                    self.atomicgraphs[graph.n3()].update({s.n3(): agraph})
                    if len(agraph.getBNodes()) > 1:
                        for node in agraph.getBNodes():
                            if node not in bnodes:
                                bnodes.append(node)
                                self.atomicgraphs[graph.n3()].update({node: agraph})

                if isinstance(o, BNode) and o.n3() not in bnodes and bnfound is False:
                    bnodes.append(o.n3())
                    agraph = AtomicGraph(o, context)
                    self.atomicgraphs[graph.n3()].update({o.n3(): agraph})
                    if len(agraph.getBNodes()) > 1:
                        for node in agraph.getBNodes():
                            if node not in bnodes:
                                bnodes.append(node)
                                self.atomicgraphs[graph.n3()].update({node: agraph})
                else:
                    continue

        bnodes = list(set(bnodes))

    def exit(self):
        """Execute actions on API shutdown."""
        return


class AtomicGraph:
    """A Class to store atomic graphs that contain a blank node."""
    def __init__(self, bnode, context):
        if isinstance(bnode, BNode) is False:
            return

        self.triples = []
        self.hash = ''
        self.context = context
        self.bNodes = []
        self.subjects = []

        self.discoverAtomicGraph(bnode)
        print(self.getAtomicGraphHash())

    def discoverAtomicGraph(self, bnode):
        """Find all triples and blank nodes that built the atomic graph for a given blank node.

        Args:
            bnode: A reference to a blank node.
        """
        if bnode.n3() in self.bNodes:
            return
        self.bNodes.append(bnode.n3())

        for s, p, o in self.context.triples((bnode, None, None)):
            self.triples.append({'s': s, 'p': p, 'o': o})
            if isinstance(o, BNode):
                self.discoverAtomicGraph(o)
        for s, p, o in self.context.triples((None, None, bnode)):
            self.triples.append({'s': s, 'p': p, 'o': o})
            if isinstance(s, BNode):
                self.discoverAtomicGraph(s)

    def getAtomicGraphHash(self):
        """Return the Hash of the entire graph.

        Returns:
            Hash: String of the sha256 hash of the graph serialization.
        """
        self.graph = Graph()
        subjects = []

        for triple in self.triples:
            self.graph.add((triple['s'], triple['p'], triple['o']))

        for s in self.graph.subjects():
            self.visited = []
            encodedSubject = self._encodeSubject(s)
            if encodedSubject != '':
                subjects.append(encodedSubject)
            subjects.append(encodedSubject)

        subjects = sorted(subjects)
        subjectString = '{' + '}{'.join(subjects) + '}'

        import hashlib
        hash = hashlib.sha256(subjectString.encode('UTF-8')).hexdigest()

        return hash

    def _encodeSubject(self, subject):
        """Encode a subject node.

        As described in 3.2 of "Hashing of RDF Graphs and a Solution to the Blank Node Problem"
        Args:
            subject: A rdflib URIRef or BNode
        Returns:
            hash:
        """
        if isinstance(subject, BNode):
            if subject in self.visited:
                return ''
            else:
                value = '*'
                self.visited.append(subject)
        else:
            value = subject.n3()

        properties = self._encodeProperties(subject)

        if properties != '':
            return value + self._encodeProperties(subject)
        else:
            return ''

    def _encodeProperties(self, subject):
        """Encode properties of a subject node.

        As described in 3.3 of "Hashing of RDF Graphs and a Solution to the Blank Node Problem"
        Args:
            subject: A rdflib URIRef or BNode
        Returns:
            hash:
        """
        predicates = []

        for p in self.graph.predicates(subject):
            objects = []
            for o in self.graph.objects(subject, p):
                encodedObject = self._encodeObject(o)
                if encodedObject != '':
                    objects.append(encodedObject)

            objects = sorted(objects)

            if len(objects) > 0:
                objectstring = '[' + ']['.join(objects) + ']'
                predicates.append('(' + p.n3() + objectstring + ')')

        predicates = sorted(predicates)
        return ''.join(predicates)

    def _encodeObject(self, object):
        """Encode object.

        As described in 3.4 of "Hashing of RDF Graphs and a Solution to the Blank Node Problem"
        Args:
            subject: A rdflib URIRef or BNode
        Returns:
            hash:
        """
        if isinstance(object, BNode):
            value = self._encodeSubject(object)
        else:
            value = object.n3()

        return value

    def getBNodes(self):
        """Return all found blank nodes of the atomic graph.

        Returns:
            BNodes: A list containing BNode objects
        """
        return self.bNodes

    def serialize(self):
        """Return all found blank nodes of the atomic graph.

        Returns:
            nquads: A nquads serialization of the atomic graph.
        """
        graphString = ''
        for triple in self.triples:
            quad = triple['s'].n3() + ' ' + triple['p'].n3() + ' ' + triple['o'].n3()
            quad+= ' <' + str(self.context.identifier) + '> .\n'
            graphString+= quad

        return graphString


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
            origin: The remote URL where to clone and fetch from and push to
        """
        logger = logging.getLogger('quit.core.GitRepo')
        logger.debug('GitRepo, init, Create an instance of GitStore')
        self.path = path

        if not exists(path):
            try:
                makedirs(path)
            except OSError as e:
                raise Exception('Can\'t create path in filesystem:', path, e)

        try:
            self.repo = Repository(path)
        except KeyError:
            pass
        except AttributeError:
            pass

        if origin:
            self.callback = QuitRemoteCallbacks()

        if self.repo:
            if self.repo.is_bare:
                raise QuitGitRepoError('Bare repositories not supported, yet')

            if origin:
                # set remote
                self.addRemote('origin', origin)
        else:
            if origin:
                # clone
                self.repo = self.cloneRepository(origin, path, self.callback)
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
            return repo
        except Exception as e:
            raise QuitGitRepoError(
                "Could not clone from: {} origin. {}".format(
                    origin,
                    e
                )
            )

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
        except Exception as e:
            logger.info("GitRepo, addfile, Could not add file  {}.".format(filename))
            logger.debug(e)

    def addRemote(self, name, url):
        """Add a remote.

        Args:
            name: A string containing the name of the remote.
            url: A string containing the url to the remote.
        """
        try:
            self.repo.remotes.create(name, url)
            logger.info("Successfully added remote: {} - {}".format(name, url))
        except Exception as e:
            logger.info("Could not add remote: {} - {}".format(name, url))
            logger.debug(e)

        try:
            self.repo.remotes.set_push_url(name, url)
            self.repo.remotes.set_url(name, url)
        except Exception as e:
            logger.info("Could not set push/fetch urls: {} - {}".format(name, url))
            logger.debug(e)

    def checkout(self, commitid):
        """Checkout a commit by a commit id.

        Args:
            commitid: A string cotaining a commitid.
        """
        try:
            commit = self.repo.revparse_single(commitid)
            self.repo.set_head(commit.oid)
            self.repo.reset(commit.oid, GIT_RESET_HARD)
            logger.info("Checked out commit: {}".format(commitid))
        except Exception as e:
            logger.info("Could not check out commit: {}".format(commitid))
            logger.debug(e)

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
            logger.info('Updates commited')
        except Exception as e:
            logger.info('Nothing to commit')
            logger.debug(e)

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
            # Check if the garbage collection process is still running
            if self.gcProcess is None or self.gcProcess.poll() is not None:
                # Start garbage collection with "--auto" option,
                # which imidietly terminates, if it is not necessary
                self.gcProcess = Popen(["git", "gc", "--auto", "--quiet"])
        except Exception as e:
            logger.debug('Git garbage collection failed to spawn')
            logger.debug(e)

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
        except Exception as e:
            logger.info("Can not pull:  Remote {} not found.".format(remote))
            logger.debug(e)

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
            logger.debug('Can not pull. Unknown merge analysis result')

    def push(self, remote='origin', branch='master'):
        """Push if possible.

        Return:
            True: If successful.
            False: If diverged or nothing to push.
        """
        ref = ['refs/heads/' + branch]

        try:
            remo = self.repo.remotes[remote]
        except Exception as e:
            logger.info("Can not push. Remote: {} does not exist.".format(remote))
            logger.debug(e)
            return

        try:
            remo.push(ref, callbacks=self.callback)
        except Exception as e:
            logger.info("Can not push to {} with ref {}".format(remote, str(ref)))
            logger.debug(e)

    def getRemotes(self):
        remotes = {}

        try:
            for remote in self.repo.remotes:
                remotes[remote.name] = [remote.url, remote.push_url]
        except Exception as e:
            logger.info('No remotes found.')
            logger.debug(e)
            return {}

        return remotes


class QuitRemoteCallbacks (RemoteCallbacks):
    """Set a pygit callback for user authentication when acting with remotes."""

    def credentials(self, url, username_from_url, allowed_types):
        """
        The callback to return a suitable authentication method.

        it supports GIT_CREDTYPE_SSH_KEY and GIT_CREDTYPE_USERPASS_PLAINTEXT
        GIT_CREDTYPE_SSH_KEY with an ssh agent configured in the env variable SSH_AUTH_SOCK
          or with id_rsa and id_rsa.pub in ~/.ssh (password must be the empty string)
        GIT_CREDTYPE_USERPASS_PLAINTEXT from the env variables GIT_USERNAME and GIT_PASSWORD
        """
        if credentials.GIT_CREDTYPE_SSH_KEY & allowed_types:
            if "SSH_AUTH_SOCK" in environ:
                # Use ssh agent for authentication
                return KeypairFromAgent(username_from_url)
            else:
                ssh = join(expanduser('~'), '.ssh')
                if "QUIT_SSH_KEY_HOME" in environ:
                    ssh = environ["QUIT_SSH_KEY_HOME"]
                # public key is still needed because:
                # _pygit2.GitError: Failed to authenticate SSH session:
                # Unable to extract public key from private key file:
                # Method unimplemented in libgcrypt backend
                pubkey = join(ssh, 'id_rsa.pub')
                privkey = join(ssh, 'id_rsa')
                # check if ssh key is available in the directory
                if isfile(pubkey) and isfile(privkey):
                    return Keypair(username_from_url, pubkey, privkey, "")
                else:
                    raise Exception(
                        "No SSH keys could be found, please specify SSH_AUTH_SOCK or add keys to " +
                        "your ~/.ssh/"
                    )
        elif credentials.GIT_CREDTYPE_USERPASS_PLAINTEXT & allowed_types:
            if "GIT_USERNAME" in environ and "GIT_PASSWORD" in environ:
                return UserPass(environ["GIT_USERNAME"], environ["GIT_PASSWORD"])
            else:
                raise Exception(
                    "Remote requested plaintext username and password authentication but " +
                    "GIT_USERNAME or GIT_PASSWORD are not set."
                )
        else:
            raise Exception("Only unsupported credential types allowed by remote end")
