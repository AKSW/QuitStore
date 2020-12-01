import pygit2
import rdflib
from atomicgraphs import comp_graph
import logging
from quit.exceptions import QuitMergeConflict, QuitBlobMergeConflict
from rdflib.plugins.serializers.nt import _nt_row as _nt
import rdflib.plugins.parsers as parsers

logger = logging.getLogger('quit.merge')


class Merger(object):
    """This class combines all neccessary methods for performing a merge on two graph commits."""

    def __init__(self, quitRepository, repository):
        """A Merger.

        Keyword arguments:
        repository -- the pygit2 Repository instance
        """
        self.quitRepository = quitRepository
        self._repository = repository

    def merge_analysis(self, target=None, branch=None):
        """Analogou reimplementation of Repository.merge_analysis.

        As of libgit2 f1323d9c161aeeada190fd9615a8b5a9fb8a7f3e "/src/merge.c".
        """
        if target == "HEAD" and self._repository.head_is_unborn:
            return pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD | pygit2.GIT_MERGE_ANALYSIS_UNBORN

        target = self.quitRepository.lookup(target)
        branch = self.quitRepository.lookup(branch)

        ancestor_head = self._repository.merge_base(target, branch)
        if ancestor_head is None:
            # TODO there might be more errors
            return pygit2.GIT_MERGE_ANALYSIS_NONE

        # We're up-to-date if we're trying to merge our own common ancestor.
        if branch == ancestor_head:
            return pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE

        # We're fastforwardable if we're our own common ancestor.
        if target == ancestor_head:
            return pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD | pygit2.GIT_MERGE_ANALYSIS_NORMAL

        return pygit2.GIT_MERGE_ANALYSIS_NORMAL

    def merge_three_way_head(self, branch):
        commitid = self.quitRepository.lookup(branch)
        self._repository.merge(commitid)

        if self._repository.index.conflicts is not None:
            for conflict in self._repository.index.conflicts:
                logger.error('Conflicts found in: {}'.format(conflict[0].path))
            raise QuitMergeConflict('Conflicts, ahhhhh!!')

        user = self._repository.default_signature
        tree = self._repository.index.write_tree()
        self._repository.create_commit(
            'HEAD', user, user, 'Merge!', tree,
            [self._repository.head.target, commitid]
        )
        # We need to do this or git CLI will think we are still merging.
        self._repository.state_cleanup()

    def merge_quit_commits(self, target, branch, favour):

        targetOid = self.quitRepository.lookup(target)
        branchOid = self.quitRepository.lookup(branch)
        baseOid = self._repository.merge_base(targetOid, branchOid)

        baseCommit = self._repository.get(baseOid)
        targetCommit = self._repository.get(targetOid)
        branchCommit = self._repository.get(branchOid)

        diff = targetCommit.tree.diff_to_tree(branchCommit.tree)

        baseTree = baseCommit.tree

        mergedTreeBuilder = self._repository.TreeBuilder(targetCommit.tree)
        logger.debug(diff)
        print("Diff: {}".format(diff))
        logger.debug(diff.stats)
        logger.debug("Diff has following patches")
        conflicts = {}
        for p in diff:
            print("Patch: {}".format(p))
            logger.debug("A Patch")
            logger.debug(p)
            logger.debug(p.line_stats)
            # logger.debug(p.patch)
            logger.debug(p.delta)
            logger.debug(p.delta.nfiles)
            logger.debug(p.delta.status_char())
            logger.debug(p.delta.status)
            logger.debug(p.delta.new_file.path)
            logger.debug(p.delta.new_file.size)
            logger.debug(p.delta.new_file.id)
            logger.debug(p.delta.old_file.path)
            logger.debug(p.delta.old_file.size)
            logger.debug(p.delta.old_file.id)
            if p.delta.status == pygit2.GIT_DELTA_UNMODIFIED:
                continue
            # TODO support merging subdirectories
            # TODO support mode changes
            # TODO support merge of moved graphs

            if p.delta.status in [pygit2.GIT_DELTA_ADDED, pygit2.GIT_DELTA_DELETED,
                                  pygit2.GIT_DELTA_MODIFIED]:
                if p.delta.old_file.path in baseTree:
                    baseOid = baseTree[p.delta.old_file.path].id
                else:
                    baseOid = pygit2.Oid(hex=pygit2.GIT_OID_HEX_ZERO)
                try:
                    mergedBlob = self._merge_graph_blobs(p.delta.old_file.id, p.delta.new_file.id,
                                                         baseOid, favour=favour)
                    mergedTreeBuilder.insert(p.delta.old_file.path, mergedBlob,
                                             p.delta.old_file.mode)
                except QuitBlobMergeConflict as mergeconflict:
                    conflicts[p.delta.old_file.path] = mergeconflict.getObject()
            else:
                raise Exception("There are operations which I don't know how to merge. yet.")

        if conflicts:
            raise QuitMergeConflict("Unfortunately, we've experienced a merge conflict!", conflicts)

        mergedTreeOid = mergedTreeBuilder.write()
        if target == "HEAD" or self._repository.head.name == target:
            print(target)
            mergedTree = self._repository.get(mergedTreeOid)
            self._repository.checkout_tree(mergedTree)

        # Create commit with our resulting tree
        user = self._repository.default_signature
        commitId = self._repository.create_commit(
            target, user, user, 'Merge graphs with {}!'.format(favour), mergedTreeOid,
            [targetOid, branchOid]
        )

        logger.debug("Created commit {} and forwarded {}".format(commitId, target))
        # We need to do this or git CLI will think we are still merging.
        self._repository.state_cleanup()

    def _merge_graph_blobs(self, graphAOid, graphBOid, graphBaseOid, favour):
        """Merge two commited graphs, with a base, into one merged blob.

        Returns:
        blob
        """
        logger.debug("blobs to merge: {} {} {}".format(graphAOid, graphBOid, graphBaseOid))
        if graphAOid == graphBaseOid:
            return graphBOid
        if graphBOid == graphBaseOid:
            return graphAOid

        if favour == "three-way":
            return self._merge_threeway_graph_blobs(graphAOid, graphBOid, graphBaseOid)
        if favour == "context":
            return self._merge_context_graph_blobs(graphAOid, graphBOid, graphBaseOid)

    def _merge_threeway_graph_blobs(self, graphAOid, graphBOid, graphBaseOid):
        if str(graphAOid) == pygit2.GIT_OID_HEX_ZERO:
            aGraph = rdflib.Graph()
        else:
            graphAblob = self._repository[graphAOid].data
            aGraph = rdflib.Graph().parse(data=graphAblob.decode("utf-8"), format="nt")

        bGraph = rdflib.Graph()
        parserGraphB = parsers.ntriples.W3CNTriplesParser(parsers.ntriples.NTGraphSink(bGraph))
        if not str(graphBOid) == pygit2.GIT_OID_HEX_ZERO:
            graphBblob = self._repository[graphBOid].data
            source = rdflib.parser.create_input_source(data=graphBblob.decode("utf-8"))
            parserGraphB.parse(source.getCharacterStream())

        if graphBaseOid is not None:
            graphBaseblob = self._repository[graphBaseOid].data
            compGraphBase = comp_graph.ComparableGraph()
            compGraphBase.parse(data=graphBaseblob.decode("utf-8"), format="nt")
            compGraphA = comp_graph.ComparableGraph(aGraph.store, aGraph.identifier)
            compGraphB = comp_graph.ComparableGraph(bGraph.store, bGraph.identifier)
            diffA = compGraphA.diff(compGraphBase)
            diffB = compGraphB.diff(compGraphBase)

            diffANewTriples = self._accumulate_triples(diffA[1])
            diffBNewTriples = self._accumulate_triples(diffB[1])
            diffARemovedTriples = self._accumulate_triples(diffA[0])
            diffBRemovedTriples = self._accumulate_triples(diffB[0])
            baseTriples = self._get_triples(compGraphBase)
            merged = (baseTriples - diffARemovedTriples - diffBRemovedTriples |
                      diffANewTriples | diffBNewTriples)
        else:
            compGraphA = comp_graph.ComparableGraph(aGraph.store, bGraph.identifier)
            compGraphB = comp_graph.ComparableGraph(bGraph.store, bGraph.identifier)
            diff = compGraphA.diff(compGraphB)
            merged = self._get_triples(compGraphA)
            merged = merged.union(self._accumulate_triples(diff[0]))
        bNodeNameMap = {}
        for bNodeName in parserGraphB._bnode_ids:
            bNodeNameMap[parserGraphB._bnode_ids[bNodeName]] = bNodeName
        merged = self._serialize_triple_sets(merged, bNodeNameMap)
        blob = self._repository.create_blob(("\n".join(merged) + "\n").encode("utf-8"))
        return blob

    def _accumulate_triples(self, setOfGraphs):
        result = set()
        for aGraph in setOfGraphs:
            result = result.union(self._get_triples(aGraph))
        return result

    def _get_triples(self, graph):
        return set(graph.triples((None, None, None)))

    def _serialize_triple_sets(self, tripleSet, bIdMap):
        result = set()
        for triple in tripleSet:
            result.add("{} {} {} .".format(self._serialize_bNode(triple[0], bIdMap),
                                           triple[1].n3(),
                                           self._serialize_bNode(triple[2], bIdMap)))
        return sorted(result)

    def _serialize_bNode(self, node, bIdMap):
        if(isinstance(node, rdflib.BNode)):
            try:
                return "_:{}".format(bIdMap[node])
            except KeyError:
                return node.n3()
        else:
            return node.n3()

    def _merge_context_graph_blobs(self, graphAOid, graphBOid, graphBaseOid):
        if str(graphAOid) == pygit2.GIT_OID_HEX_ZERO:
            graphA = comp_graph.ComparableGraph()
        else:
            graphAblob = self._repository[graphAOid].data
            graphA = comp_graph.ComparableGraph()
            graphA.parse(data=graphAblob.decode("utf-8"), format="nt")

        if str(graphBOid) == pygit2.GIT_OID_HEX_ZERO:
            graphB = comp_graph.ComparableGraph()
        else:
            graphBblob = self._repository[graphBOid].data
            graphB = comp_graph.ComparableGraph()
            graphB.parse(data=graphBblob.decode("utf-8"), format="nt")

        if graphBaseOid is not None:
            graphBaseblob = self._repository[graphBaseOid].data
            graphBase = comp_graph.ComparableGraph()
            graphBase.parse(data=graphBaseblob.decode("utf-8"), format="nt")
        else:
            graphBase = comp_graph.ComparableGraph()

        diffA = graphA.diff(graphBase)
        diffB = graphB.diff(graphBase)

        diffANewTriples = self._accumulate_triples(diffA[1])
        diffBNewTriples = self._accumulate_triples(diffB[1])
        diffARemovedTriples = self._accumulate_triples(diffA[0])
        diffBRemovedTriples = self._accumulate_triples(diffB[0])
        baseTriples = self._get_triples(graphBase)
        merged = (baseTriples - diffARemovedTriples - diffBRemovedTriples +
                  diffANewTriples + diffBNewTriples)
        serializer = parsers.ntriples.NTriplesParser(parsers.nt.NTSink(graphA))
        merged = self._serialize_triple_sets(merged, serializer._bnode_ids)

        blob = self._repository.create_blob("\n".join(merged).encode("utf-8"))
        return blob

    def _compare_atomic_graphs(self, graphDataA, graphDataB):
        aGraph = comp_graph.ComparableGraph()
        aGraph.parse(data=graphDataA, format="n3")
        bGraph = comp_graph.ComparableGraph()
        bGraph.parse(data=graphDataB, format="n3")
        aData = aGraph.serialize(destination=None, format='nt')
        diffData = aGraph.diff(bGraph)[1].serialize(destination=None, format='nt')
        return aData + diffData

    def _merge_context_conflict_detection(self, addA, delA, addB, delB):

        def conflictSet(graph, conflictingNodes):
            ok = set()
            conflicts = set()
            for triple in graph.triples((None, None, None)):
                if triple[0] in conflictingNodes or triple[2] in conflictingNodes:
                    conflicts.add(_nt(triple).rstrip())
                else:
                    ok.add(_nt(triple).rstrip())
            return ok, conflicts

        graphAddA = rdflib.ConjunctiveGraph()
        graphAddA.parse(data="\n".join(addA), format="nt")
        graphAddB = rdflib.ConjunctiveGraph()
        graphAddB.parse(data="\n".join(addB), format="nt")
        graphDelA = rdflib.ConjunctiveGraph()
        graphDelA.parse(data="\n".join(delA), format="nt")
        graphDelB = rdflib.ConjunctiveGraph()
        graphDelB.parse(data="\n".join(delB), format="nt")

        conflictingNodes = (graphAddA + graphDelA).all_nodes().intersection(
            (graphAddB + graphDelB).all_nodes())
        print(conflictingNodes)
        logger.debug(conflictingNodes)

        conflicts = {}
        ok = set()

        for key, graph in [("addA", graphAddA), ("delA", graphDelA),
                           ("addB", graphAddB), ("delB", graphDelB)]:
            newOK, conflict = conflictSet(graph, conflictingNodes)
            if len(conflict) > 0:
                conflicts[key] = "\n".join(sorted(conflict))
            if key.startswith("add"):
                ok.update(newOK)

        print("list done")

        if conflicts:
            nodes = []
            for node in conflictingNodes:
                logger.debug(node.n3())
                nodes.append(node.n3())
            conflicts["nodes"] = nodes
        print(conflicts)

        print("OK")
        print(ok)

        return sorted(ok), conflicts or None
