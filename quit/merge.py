import os
import pygit2
import rdflib
import logging
from quit.exceptions import QuitMergeConflict, QuitBlobMergeConflict
from rdflib.plugins.serializers.nquads import _nq_row as _nq

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
        self._repository.merge(branch)

        if self._repository.index.conflicts is not None:
            for conflict in self._repository.index.conflicts:
                logger.error('Conflicts found in: {}'.format(conflict[0].path))
            raise QuitMergeConflict('Conflicts, ahhhhh!!')

        user = self._repository.default_signature
        tree = self._repository.index.write_tree()
        self._repository.create_commit(
            'HEAD', user, user, 'Merge!', tree,
            [self._repository.head.target, branch]
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

        logger.debug(diff.stats)
        logger.debug("Diff has following patches")
        conflicts = {}
        for p in diff:
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
                    baseOid = None
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

        mergedTree = mergedTreeBuilder.write()

        # Create commit with our resulting tree
        user = self._repository.default_signature
        commitId = self._repository.create_commit(
            target, user, user, 'Merge graphs with {}!'.format(favour), mergedTree,
            [targetOid, branchOid]
        )
        logger.debug("Created commit {} and forwarded {}".format(commitId, target))
        # We need to do this or git CLI will think we are still merging.
        self._repository.state_cleanup()

    def _merge_graph_blobs(self, graphAOid, graphBOid, graphBaseOid, favour):
        """Merge two commited graphs, with a base, into one merged blob.

        Returns:
        blob, conflicts
        """
        logger.debug("{} {} {}".format(graphAOid, graphBOid, graphBaseOid))
        if graphAOid == graphBaseOid:
            return graphBOid, None
        if graphBOid == graphBaseOid:
            return graphAOid, None

        if favour == "three-way":
            return self._merge_threeway_graph_blobs(graphAOid, graphBOid, graphBaseOid)
        if favour == "context":
            return self._merge_context_graph_blobs(graphAOid, graphBOid, graphBaseOid)

    def _merge_threeway_graph_blobs(self, graphAOid, graphBOid, graphBaseOid):
        if str(graphAOid) == pygit2.GIT_OID_HEX_ZERO:
            a = set()
        else:
            graphAblob = self._repository[graphAOid].data
            a = set(graphAblob.decode("utf-8").split("\n"))

        if str(graphBOid) == pygit2.GIT_OID_HEX_ZERO:
            b = set()
        else:
            graphBblob = self._repository[graphBOid].data
            b = set(graphBblob.decode("utf-8").split("\n"))

        if graphBaseOid is not None:
            graphBaseblob = self._repository[graphBaseOid].data
            base = set(graphBaseblob.decode("utf-8").split("\n"))
            addA = a - base
            addB = b - base
            intersect = a.intersection(b)
            merged = sorted(intersect.union(addA).union(addB))
        else:
            merged = a.union(b)
        print("\n".join(merged))

        blob = self._repository.create_blob("\n".join(merged).encode("utf-8"))
        return blob

    def _merge_context_graph_blobs(self, graphAOid, graphBOid, graphBaseOid):
        if str(graphAOid) == pygit2.GIT_OID_HEX_ZERO:
            a = set()
        else:
            graphAblob = self._repository[graphAOid].data
            a = set(graphAblob.decode("utf-8").split("\n"))

        if str(graphBOid) == pygit2.GIT_OID_HEX_ZERO:
            b = set()
        else:
            graphBblob = self._repository[graphBOid].data
            b = set(graphBblob.decode("utf-8").split("\n"))

        if graphBaseOid is not None:
            graphBaseblob = self._repository[graphBaseOid].data
            base = set(graphBaseblob.decode("utf-8").split("\n"))
        else:
            base = set()

        logger.debug("base")
        logger.debug(base)
        logger.debug("a")
        logger.debug(a)
        logger.debug("b")
        logger.debug(b)

        addA = a - base
        delA = base - a
        addB = b - base
        delB = base - b

        ok, conflicts = self._merge_context_conflict_detection(addA - addB, delA - delB,
                                                               addB - addA, delB - delA)

        logger.debug("intersect and ok, then merged")
        logger.debug(a.intersection(b))
        logger.debug(ok)
        merged = sorted(a.intersection(b).union(ok))
        logger.debug(merged)
        print(merged)

        if conflicts is not None:
            print("raised")
            raise QuitBlobMergeConflict('Conflicts, ahhhhh!!', merged, conflicts)

        blob = self._repository.create_blob("\n".join(merged).encode("utf-8"))
        return blob

    def _merge_context_conflict_detection(self, addA, delA, addB, delB):

        def conflictSet(graph, conflictingNodes):
            ok = set()
            conflicts = set()
            for triple in graph.quads((None, None, None, None)):
                if triple[0] in conflictingNodes or triple[2] in conflictingNodes:
                    conflicts.add(_nq(triple[:3], triple[3].identifier).rstrip())
                else:
                    ok.add(_nq(triple[:3], triple[3].identifier).rstrip())
            return ok, conflicts

        graphAddA = rdflib.ConjunctiveGraph()
        graphAddA.parse(data="\n".join(addA), format="nquads")
        graphAddB = rdflib.ConjunctiveGraph()
        graphAddB.parse(data="\n".join(addB), format="nquads")
        graphDelA = rdflib.ConjunctiveGraph()
        graphDelA.parse(data="\n".join(delA), format="nquads")
        graphDelB = rdflib.ConjunctiveGraph()
        graphDelB.parse(data="\n".join(delB), format="nquads")

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
