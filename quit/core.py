import pygit2

import logging

from pygit2 import GIT_MERGE_ANALYSIS_UP_TO_DATE
from pygit2 import GIT_MERGE_ANALYSIS_FASTFORWARD
from pygit2 import GIT_MERGE_ANALYSIS_NORMAL
from pygit2 import GIT_SORT_REVERSE, GIT_RESET_HARD, GIT_STATUS_CURRENT

from rdflib import Graph, ConjunctiveGraph, BNode, Literal
from rdflib.plugins.serializers.nquads import _nq_row as _nq

from quit.conf import Feature
from quit.namespace import RDFS, FOAF, XSD, PROV, QUIT, is_a
from quit.graphs import RewriteGraph, InMemoryAggregatedGraph
from quit.utils import graphdiff, git_timestamp
from quit.cache import Cache, FileReference

import subprocess

logger = logging.getLogger('quit.core')


class Queryable:
    """A class that represents a querable graph-like object."""

    def __init__(self, **kwargs):
        pass

    def query(self, querystring):
        """Execute a SPARQL select query.

        Args:
            querystring: A string containing a SPARQL ask or select query.
        Returns:
            The SPARQL result set
        """
        pass

    def update(self, querystring):
        """Execute a SPARQL update query and update the store.

        This method executes a SPARQL update query and updates and commits all affected files.

        Args:
            querystring: A string containing a SPARQL upate query.
        """
        pass


class Store(Queryable):
    """A class that combines and syncronieses n-quad files and an in-memory quad store.

    This class contains information about all graphs, their corresponding URIs and
    pathes in the file system. For every Graph (context of Quad-Store) exists a
    FileReference object (n-quad) that enables versioning (with git) and persistence.
    """

    def __init__(self, store):
        """Initialize a new Store instance."""
        self.store = store

        return


class MemoryStore(Store):
    def __init__(self, additional_bindings=list()):
        store = ConjunctiveGraph(identifier='default')
        nsBindings = [('quit', QUIT), ('foaf', FOAF), ('prov', PROV)]

        for prefix, namespace in nsBindings + additional_bindings:
            store.bind(prefix, namespace)

        super().__init__(store=store)


class VirtualGraph(Queryable):
    def __init__(self, store):
        if not isinstance(store, InMemoryAggregatedGraph):
            raise Exception()
        self.store = store

    def query(self, querystring):
        return self.store.query(querystring)

    def update(self, querystring):
        return self.store.update(querystring)


class Quit(object):
    """Quit object which keeps the store syncronised with the repository."""

    gcProcess = None

    def __init__(self, config, repository, store):
        self.config = config
        self.repository = repository
        self.store = store
        self._commits = Cache()
        self._blobs = Cache()

    def _exists(self, cid):
        uri = QUIT['commit-' + cid]
        for _ in self.store.store.quads((uri, None, None, QUIT.default)):
            return True
        return False

    def rebuild(self):
        for context in self.store.contexts():
            self.store.remove((None, None, None), context)
        self.syncAll()

    def syncAll(self):
        """Synchronize store with repository data."""
        def traverse(commit, seen):
            commits = []
            merges = []

            while True:
                id = commit.id
                if id in seen:
                    break
                seen.add(id)
                if self._exists(id):
                    break
                commits.append(commit)
                parents = commit.parents
                if not parents:
                    break
                commit = parents[0]
                if len(parents) > 1:
                    merges.append((len(commits), parents[1:]))
            for idx, parents in reversed(merges):
                for parent in parents:
                    commits[idx:idx] = traverse(parent, seen)
            return commits

        seen = set()

        for name in self.repository.tags_or_branches:
            initial_commit = self.repository.revision(name)
            commits = traverse(initial_commit, seen)

            while commits:
                commit = commits.pop()
                self.syncSingle(commit)

    def syncSingle(self, commit, delta=None):
        if not self._exists(commit.id):
            self.changeset(commit, delta)

    def instance(self, commit_id=None, force=False):
        """Create and return dataset for a given commit id.

        Args:
            id: commit id of the commit to retrieve
            force: force to get the dataset from the git repository instead of the internal cache
        Returns:
            Instance of VirtualGraph representing the respective dataset
        """

        default_graphs = []

        if commit_id:
            commit = self.repository.revision(commit_id)

            for blob in self.getFilesForCommit(commit):
                try:
                    (name, oid) = blob
                    f, contexts = self.getFileReferenceAndContext(blob, commit)
                    for context in contexts:
                        internal_identifier = context.identifier + '-' + str(oid)

                        if force or not self.config.hasFeature(Feature.Persistence):
                            g = context
                        else:
                            g = RewriteGraph(
                                self.store.store.store,
                                internal_identifier,
                                context.identifier
                            )
                        default_graphs.append(g)
                except KeyError:
                    pass

        instance = InMemoryAggregatedGraph(
            graphs=default_graphs, identifier='default')

        return VirtualGraph(instance)

    def changeset(self, commit, delta=None):

        if (
            not self.config.hasFeature(Feature.Persistence)
        ) and (
            not self.config.hasFeature(Feature.Provenance)
        ):
            return

        g = self.store.store

        if self.config.hasFeature(Feature.Provenance):
            role_author_uri = QUIT['Author']
            role_committer_uri = QUIT['Committer']

            g.add((role_author_uri, is_a, PROV['Role']))
            g.add((role_committer_uri, is_a, PROV['Role']))

        # Create the commit
        i1 = self.instance(commit.id, True)

        commit_uri = QUIT['commit-' + commit.id]

        if self.config.hasFeature(Feature.Provenance):
            g.add((commit_uri, is_a, PROV['Activity']))

            if 'Source' in commit.properties.keys():
                g.add((commit_uri, is_a, QUIT['Import']))
                g.add((commit_uri, QUIT['dataSource'], Literal(
                    commit.properties['Source'].strip())))
            if 'Query' in commit.properties.keys():
                g.add((commit_uri, is_a, QUIT['Transformation']))
                g.add((commit_uri, QUIT['query'], Literal(
                    commit.properties['Query'].strip())))

            g.add((commit_uri, QUIT['hex'], Literal(commit.id)))
            g.add((commit_uri, PROV['startedAtTime'], Literal(
                git_timestamp(commit.author.time, commit.author.offset),
                datatype=XSD.dateTime)))
            g.add((commit_uri, PROV['endedAtTime'], Literal(
                git_timestamp(commit.committer.time, commit.committer.offset),
                datatype=XSD.dateTime)))
            g.add((commit_uri, RDFS['label'],
                   Literal(commit.message.strip())))

            # Author
            hash = pygit2.hash(commit.author.email).hex
            author_uri = QUIT['user-' + hash]
            g.add((commit_uri, PROV['wasAssociatedWith'], author_uri))

            g.add((author_uri, is_a, PROV['Agent']))
            g.add((author_uri, RDFS.label, Literal(commit.author.name)))
            g.add((author_uri, FOAF.mbox, Literal(commit.author.email)))

            q_author_uri = BNode()
            g.add((commit_uri, PROV['qualifiedAssociation'], q_author_uri))
            g.add((q_author_uri, is_a, PROV['Association']))
            g.add((q_author_uri, PROV['agent'], author_uri))
            g.add((q_author_uri, PROV['role'], role_author_uri))

            if commit.author.name != commit.committer.name:
                # Committer
                hash = pygit2.hash(commit.committer.email).hex
                committer_uri = QUIT['user-' + hash]
                g.add((commit_uri, PROV['wasAssociatedWith'], committer_uri))

                g.add((committer_uri, is_a, PROV['Agent']))
                g.add((committer_uri, RDFS.label, Literal(commit.committer.name)))
                g.add((committer_uri, FOAF.mbox, Literal(commit.committer.email)))

                q_committer_uri = BNode()
                g.add(
                    (commit_uri, PROV['qualifiedAssociation'], q_committer_uri))
                g.add((q_committer_uri, is_a, PROV['Association']))
                g.add((q_committer_uri, PROV['agent'], author_uri))
                g.add((q_committer_uri, PROV['hadRole'], role_committer_uri))
            else:
                g.add((q_author_uri, PROV['hadRole'], role_committer_uri))

            # Parents
            for parent in iter(commit.parents or []):
                parent_uri = QUIT['commit-' + parent.id]
                g.add((commit_uri, QUIT["preceedingCommit"], parent_uri))
                g.add((commit_uri, PROV["wasInformedBy"], parent_uri))

            # Diff
            if not delta:
                parent = next(iter(commit.parents or []), None)

                i2 = self.instance(parent.id, True) if parent else None

                delta = graphdiff(i2.store if i2 else None, i1.store)

            for index, (iri, changesets) in enumerate(delta.items()):
                update_uri = QUIT['update-{}-{}'.format(commit.id, index)]
                g.add((update_uri, QUIT['graph'], iri))
                g.add((commit_uri, QUIT['updates'], update_uri))
                for (op, triples) in changesets:
                    op_uri = QUIT[op + '-' + commit.id]
                    g.add((update_uri, QUIT[op], op_uri))
                    g.addN((s, p, o, op_uri) for s, p, o in triples)

        # Entities
        map = self.config.getgraphurifilemap()

        for entity in commit.node().entries(recursive=True):
            # todo check if file was changed
            if entity.is_file:

                if entity.name not in map.values():
                    continue

                graphUris = self.config.getgraphuriforfile(entity.name)
                graphsFromConfig = set((Graph(identifier=i) for i in graphUris))

                blob = (entity.name, entity.oid)

                try:
                    f, contexts = self.getFileReferenceAndContext(blob, commit)
                except KeyError:
                    tmp = ConjunctiveGraph()
                    tmp.parse(data=entity.content, format='nquads')

                    # Info: currently filter graphs from file that were not defined in config
                    # Todo: is this the wanted behaviour?
                    contexts = set((context for context in tmp.contexts(None)
                                    if context.identifier in map)) | graphsFromConfig

                    self._blobs.set(
                        blob, (FileReference(entity.name, entity.content), contexts)
                    )

                for index, context in enumerate(contexts):
                    private_uri = QUIT["graph-{}-{}".format(entity.oid, index)]

                    if (
                        self.config.hasFeature(Feature.Provenance) or
                        self.config.hasFeature(Feature.Persistence)
                    ):
                        g.add((private_uri, is_a, PROV['Entity']))
                        g.add(
                            (private_uri, PROV['specializationOf'], context.identifier))
                        g.add(
                            (private_uri, PROV['wasGeneratedBy'], commit_uri))

                        q_usage = BNode()
                        g.add((private_uri, PROV['qualifiedGeneration'], q_usage))
                        g.add((q_usage, is_a, PROV['Generation']))
                        g.add((q_usage, PROV['activity'], commit_uri))

                        prev = next(entity.history(), None)
                        if prev:
                            prev_uri = QUIT["graph-{}-{}".format(prev.oid, index)]
                            g.add((private_uri, PROV['wasDerivedFrom'], prev_uri))
                            g.add((commit_uri, PROV['used'], prev_uri))

                            q_derivation = BNode()
                            g.add((private_uri, PROV['qualifiedDerivation'], q_derivation))
                            g.add((q_derivation, is_a, PROV['Derivation']))
                            g.add((q_derivation, PROV['entity'], prev_uri))
                            g.add((q_derivation, PROV['hadActivity'], commit_uri))
                    if self.config.hasFeature(Feature.Persistence):
                        g.addN((s, p, o, private_uri) for s, p, o
                               in context.triples((None, None, None)))

    def getFilesForCommit(self, commit):
        """Get all entry, oid tupples for a commit.

        On Cache miss this method also updates teh commits cache.
        """
        uriFileMap = self.config.getgraphurifilemap()

        if commit.id not in self._commits:
            blobs = set()
            for entity in commit.node().entries(recursive=True):
                if entity.is_file:
                    if entity.name not in uriFileMap.values():
                        continue
                    blob = (entity.name, entity.oid)
                    blobs.add(blob)
            self._commits.set(commit.id, blobs)
            return blobs
        return self._commits.get(commit.id)

    def getFileReferenceAndContext(self, blob, commit):
        """Get the FielReference and Context for a given blob (name, oid) of a commit.

        On Cache miss this method also updates teh commits cache.
        """
        uriFileMap = self.config.getgraphurifilemap()

        if blob not in self._blobs:
            (name, oid) = blob
            content = commit.node(path=name).content
            # content = self.repository._repository[oid].data
            graphUris = self.config.getgraphuriforfile(name)
            graphsFromConfig = set((Graph(identifier=i) for i in graphUris))
            tmp = ConjunctiveGraph()
            tmp.parse(data=content, format='nquads')
            contexts = set((context for context in tmp.contexts(None)
                            if context.identifier in uriFileMap)) | graphsFromConfig
            quitWorkingData = (FileReference(name, content), contexts)
            self._blobs.set(
                blob, quitWorkingData)
            return quitWorkingData
        return self._blobs.get(blob)

    def commit(self, graph, delta, message, commit_id, ref, query=None, default_graph=[],
               named_graph=[], **kwargs):
        """Commit changes after applying deltas to the blobs.

        This methods analyzes the delta an apllies the changes to the blobs of the repository.
        A commit message is built with help of message and if called from endpoint with query,
        default_graph and named_graph. **kwargs can be used to extend the commit message with
        custom key-value-pairs.

        Args:
            graph: the current graph instance
            delta: delta that will be applied
            message: commit message
            commit_id: the commit-id of preceeding commit
            ref: a ref/branch were the commit will be applied to
            query: the query that lead to the commit
            default_graph: using-graph-uri values from SPARQL protocol
            named_graph: using-named-graph-uri values from SPARQL protocol
        """
        def build_message(message, kwargs):
            out = list()
            if message:
                out.append(message)
                out.append('')
            if query:
                out.append('query: {}'.format(query))
            if isinstance(default_graph, list) and len(default_graph) > 0:
                out.append('using-graph-uri: {}'.format(', '.join(default_graph)))
            if isinstance(named_graph, list) and len(named_graph) > 0:
                out.append('using-named-graph-uri: {}'.format(', '.join(named_graph)))
            for k, v in kwargs.items():
                out.append('{}: "{}"'.format(k, v.replace('"', "\\\"")))
            return "\n".join(out)

        def _apply(f, changeset, identifier):
            """Update the FileReference (graph uri) of a file with help of the changeset."""
            for (op, triples) in changeset:
                if op == 'additions':
                    for triple in triples:
                        # the internal _nq serializer appends '\n'
                        line = _nq(triple, identifier).rstrip()
                        f.add(line)
                elif op == 'removals':
                    for triple in triples:
                        # the internal _nq serializer appends '\n'
                        line = _nq(triple, identifier).rstrip()
                        f.remove(line)

        if not delta:
            return

        commit = self.repository.revision(commit_id)
        index = self.repository.index(commit.id)

        blobs_new = set()
        try:
            blobs = self.getFilesForCommit(commit)
        except KeyError:
            blobs = []

        for blob in blobs:
            (fileName, oid) = blob
            try:
                file_reference, contexts = self.getFileReferenceAndContext(blob, commit)
                for context in contexts:
                    for entry in delta:
                        changeset = entry.get(context.identifier, None)

                        if changeset:
                            _apply(file_reference, changeset, context.identifier)
                            del(entry[context.identifier])

                index.add(file_reference.path, file_reference.content)

                self._blobs.remove(blob)
                blob = fileName, index.stash[file_reference.path][0]
                self._blobs.set(blob, (file_reference, contexts))
                blobs_new.add(blob)
            except KeyError:
                pass

        unassigned = set()
        f_name = self.config.getGlobalFile() or 'unassigned.nq'
        f_new = FileReference(f_name, "")
        for entry in delta:
            for identifier, changeset in entry.items():
                unassigned.add(graph.store.get_context(identifier))
                _apply(f_new, changeset, graph.store.identifier)

                index.add(f_new.path, f_new.content)

                blob = f_name, index.stash[f_new.path][0]
                self._blobs.set(blob, (f_new, unassigned))
                blobs_new.add(blob)

        message = build_message(message, kwargs)
        author = self.repository._repository.default_signature

        oid = index.commit(message, author.name, author.email, ref=ref)

        if self.config.hasFeature(Feature.GarbageCollection):
            self.garbagecollection()

        if oid:
            self._commits.set(oid.hex, blobs_new)
            commit = self.repository.revision(oid.hex)
            if not self.repository.is_bare:
                self.repository._repository.checkout(
                    ref, strategy=pygit2.GIT_CHECKOUT_FORCE)
            self.syncSingle(commit, delta)

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
                self.gcProcess = subprocess.Popen(
                    ["git", "gc", "--auto", "--quiet"], cwd=self.repository.path
                )
            logger.debug('Spawn git garbage collection.')
        except Exception as e:
            logger.debug('Git garbage collection failed to spawn.')
            logger.debug(e)
