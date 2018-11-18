import pygit2

import logging

from copy import copy

from pygit2 import GIT_MERGE_ANALYSIS_UP_TO_DATE
from pygit2 import GIT_MERGE_ANALYSIS_FASTFORWARD
from pygit2 import GIT_MERGE_ANALYSIS_NORMAL
from pygit2 import GIT_SORT_REVERSE, GIT_RESET_HARD, GIT_STATUS_CURRENT

from rdflib import Graph, ConjunctiveGraph, BNode, Literal, URIRef
import re

from quit.conf import Feature, QuitGraphConfiguration
from quit.helpers import applyChangeset
from quit.namespace import RDFS, FOAF, XSD, PROV, QUIT, is_a
from quit.graphs import RewriteGraph, InMemoryAggregatedGraph
from quit.utils import graphdiff, git_timestamp, iri_to_name
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
        self._graphconfigs = Cache()

    def _exists(self, cid):
        uri = QUIT['commit-' + cid]
        for _ in self.store.store.quads((uri, None, None, QUIT.default)):
            return True
        return False

    def getDefaultBranch(self):
        """Get the default branch for the Git repository which should be used in the application.

        This will be the default branch as configured, if it is configured or the current HEAD of
        the repository if the HEAD is born. Will default to "master"

        Returns:
            A string containing the branch name.
        """
        config_default_branch = self.config.getDefaultBranch()
        if config_default_branch:
            return config_default_branch
        repository_current_head = self.repository.current_head
        if repository_current_head:
            return repository_current_head
        return "master"

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

    def syncSingle(self, commit):
        if not self._exists(commit.id):
            self.changeset(commit)

    def instance(self, reference, force=False):
        """Create and return dataset for a given commit id.

        Args:
            reference: commit id or reference of the commit to retrieve
            force: force to get the dataset from the git repository instead of the internal cache
        Returns:
            Instance of VirtualGraph representing the respective dataset
        """
        default_graphs = []
        commitid = None

        if reference:
            commit = self.repository.revision(reference)
            commitid = commit.id

            for blob in self.getFilesForCommit(commit):
                try:
                    (name, oid) = blob
                    (f, context) = self.getFileReferenceAndContext(blob, commit)
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

        return VirtualGraph(instance), commitid

    def changeset(self, commit):

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
        i1, commitid = self.instance(commit.id, True)

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
            parent = next(iter(commit.parents or []), None)

            i2, commitid = self.instance(parent.id, True) if parent else (None, None)

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
        if commit.id not in self._graphconfigs:
            self.updateGraphConfig(commit.id)

        map = self._graphconfigs.get(commit.id).getgraphurifilemap()

        for entity in commit.node().entries(recursive=True):
            # todo check if file was changed
            if entity.is_file:

                if entity.name not in map.values():
                    continue

                graphUri = self._graphconfigs.get(commit.id).getgraphuriforfile(entity.name)
                blob = (entity.name, entity.oid)

                try:
                    f, context = self.getFileReferenceAndContext(blob, commit)
                except KeyError:
                    graph = Graph(identifier=graphUri)
                    graph.parse(data=entity.content, format='nt')

                    self._blobs.set(
                        blob, (FileReference(entity.name, entity.content), graph)
                    )

                private_uri = QUIT["graph-{}".format(entity.oid)]

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

        On Cache miss this method also updates the commits cache.
        """

        if commit is None:
            return set()

        if commit.id not in self._commits:
            if commit.id not in self._graphconfigs:
                self.updateGraphConfig(commit.id)

            uriFileMap = self._graphconfigs.get(commit.id).getgraphurifilemap()
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
        """Get the FileReference and Context for a given blob (name, oid) of a commit.

        On Cache miss this method also updates teh commits cache.
        """
        if commit.id not in self._graphconfigs:
            self.updateGraphConfig(commit.id)

        if blob not in self._blobs:
            (name, oid) = blob
            content = commit.node(path=name).content
            graphUri = self._graphconfigs.get(commit.id).getgraphuriforfile(name)
            graph = Graph(identifier=URIRef(graphUri))
            graph.parse(data=content, format='nt')
            quitWorkingData = (FileReference(name, content), graph)
            self._blobs.set(blob, quitWorkingData)
            return quitWorkingData
        return self._blobs.get(blob)

    def commit(self, graph, delta, message, parent_commit_ref, target_ref, query=None,
               default_graph=[], named_graph=[], **kwargs):
        """Commit changes after applying deltas to the blobs.

        This methods analyzes the delta and applies the changes to the blobs of the repository.
        A commit message is built with help of message and if called from endpoint with query,
        default_graph and named_graph. **kwargs can be used to extend the commit message with
        custom key-value-pairs.

        Args:
            graph: the current graph instance
            delta: delta that will be applied
            message: commit message
            parent_commit_ref: the commit-id of preceeding commit
            target_ref: a ref/branch were the commit will be applied to
            query: the query that lead to the commit
            default_graph: using-graph-uri values from SPARQL protocol
            named_graph: using-named-graph-uri values from SPARQL protocol
        Returns:
            The newly created commits id
        """
        def build_message(message, **kwargs):
            out = list()
            if message:
                out.append(message)
                out.append('')
            if query:
                out.append('query: "{}"'.format(query.replace('"', "\\\"")))
            if source:
                out.append('source: "{}"'.format(source.replace('"', "\\\"")))
            if isinstance(default_graph, list) and len(default_graph) > 0:
                out.append('using-graph-uri: {}'.format(', '.join(default_graph)))
            if isinstance(named_graph, list) and len(named_graph) > 0:
                out.append('using-named-graph-uri: {}'.format(', '.join(named_graph)))
            for k, v in kwargs.items():
                out.append('{}: "{}"'.format(k, v.replace('"', "\\\"")))
            return "\n".join(out)

        def _applyKnownGraphs(delta, blobs):
            blobs_new = set()
            for blob in blobs:
                (fileName, oid) = blob
                try:
                    file_reference, context = self.getFileReferenceAndContext(blob, parent_commit)
                    for entry in delta:
                        changeset = entry.get(context.identifier, None)

                        if changeset:
                            applyChangeset(file_reference, changeset, context.identifier)
                            del(entry[context.identifier])

                    index.add(file_reference.path, file_reference.content)

                    self._blobs.remove(blob)
                    blob = fileName, index.stash[file_reference.path][0]
                    self._blobs.set(blob, (file_reference, context))
                    blobs_new.add(blob)
                except KeyError:
                    pass
            return blobs_new

        def _applyUnknownGraphs(delta, known_blobs):
            new_contexts = {}
            for entry in delta:
                for identifier, changeset in entry.items():
                    if isinstance(identifier, BNode) or str(identifier) == 'default':
                        continue  # TODO default graph use case

                    if identifier not in new_contexts.keys():
                        fileName = iri_to_name(identifier) + '.nt'

                        if fileName in known_blobs:
                            reg = re.compile(re.escape(iri_to_name(identifier)) + "_([0-9]+).nt")
                            #  n ~ numbers (in blobname), b ~ blobname, m ~ match
                            n = [
                                int(m.group(1)) for b in known_blobs for m in [reg.search(b)] if m
                            ] + [0]
                            fileName = '{}_{}.nt'.format(iri_to_name(identifier), max(n)+1)

                        new_contexts[identifier] = FileReference(fileName, '')

                    fileReference = new_contexts[identifier]
                    applyChangeset(fileReference, changeset, identifier)
            return new_contexts

        if not delta:
            return

        parent_commit_id = None
        parent_commit = None
        blobs = []
        blobs_new = set()

        if parent_commit_ref:
            parent_commit = self.repository.revision(parent_commit_ref)
        if parent_commit:
            parent_commit_id = parent_commit.id
            try:
                blobs = self.getFilesForCommit(parent_commit)
            except KeyError:
                pass
        index = self.repository.index(parent_commit_id)

        if parent_commit_id not in self._graphconfigs:
            self.updateGraphConfig(parent_commit_id)

        graphconfig = self._graphconfigs.get(parent_commit_id)
        known_files = graphconfig.getfiles().keys()

        blobs_new = _applyKnownGraphs(delta, blobs)
        new_contexts = _applyUnknownGraphs(delta, known_files)
        new_config = copy(graphconfig)

        for identifier, fileReference in new_contexts.items():
            # Add new blobs to repo
            index.add(fileReference.path, fileReference.content)
            if graphconfig.mode == 'graphfiles':
                index.add(fileReference.path + '.graph', identifier + "\n")

            # Update config
            new_config.addgraph(identifier, fileReference.path, 'nt')

            # Update Cache and add new contexts to store
            blob = fileReference.path, index.stash[fileReference.path][0]
            self._blobs.set(blob, (fileReference, graph.store.get_context(identifier)))
            blobs_new.add(blob)
        if graphconfig.mode == 'configuration':
            index.add('config.ttl', new_config.graphconf.serialize(format='turtle').decode())

        source = None
        if delta["type_"] == "LOAD":
            source = delta["graph"]
        message = build_message(message, query=query, source=source, **kwargs)
        author = self.repository._repository.default_signature

        oid = index.commit(message, author.name, author.email, ref=target_ref)

        if self.config.hasFeature(Feature.GarbageCollection):
            self.garbagecollection()

        if oid:
            self._commits.set(oid.hex, blobs_new)
            commit = self.repository.revision(oid.hex)
            if not self.repository.is_bare:
                self.repository._repository.checkout(
                    target_ref, strategy=pygit2.GIT_CHECKOUT_FORCE)
            self.syncSingle(commit)

        return oid.hex

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

    def updateGraphConfig(self, commitId):
        """Update the graph configuration for a given commit id."""
        graphconf = QuitGraphConfiguration(self.repository._repository)
        graphconf.initgraphconfig(commitId)
        self._graphconfigs.set(commitId, graphconf)
