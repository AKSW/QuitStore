import pygit2
import rdflib
from atomicgraphs import comp_graph
import logging
from quit.exceptions import QuitMergeConflict, QuitBlobMergeConflict
from rdflib.plugins.serializers.nt import _quoteLiteral as _qLiteral
import rdflib.plugins.parsers as parsers
import rdflib.plugins.parsers.ntriples as ntriples

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
        aGraph = comp_graph.ComparableGraph()
        parserGraphA = ntriples.W3CNTriplesParser(ntriples.NTGraphSink(aGraph))
        if not str(graphAOid) == pygit2.GIT_OID_HEX_ZERO:
            graphAblob = self._repository[graphAOid].data
            source = rdflib.parser.create_input_source(data=graphAblob.decode("utf-8"))
            parserGraphA.parse(source.getCharacterStream())

        bGraph = comp_graph.ComparableGraph()
        parserGraphB = ntriples.W3CNTriplesParser(ntriples.NTGraphSink(bGraph))
        if not str(graphBOid) == pygit2.GIT_OID_HEX_ZERO:
            graphBblob = self._repository[graphBOid].data
            source = rdflib.parser.create_input_source(data=graphBblob.decode("utf-8"))
            parserGraphB.parse(source.getCharacterStream())

        nameNodeBaseMap = None
        if graphBaseOid is not None:
            graphBaseblob = self._repository[graphBaseOid].data
            compGraphBase = comp_graph.ComparableGraph()
            parserGraphBase = ntriples.W3CNTriplesParser(ntriples.NTGraphSink(compGraphBase))
            source = rdflib.parser.create_input_source(data=graphBaseblob.decode("utf-8"))
            parserGraphBase.parse(source.getCharacterStream())
            nameNodeBaseMap = parserGraphBase._bnode_ids
            diffA = aGraph.diff(compGraphBase)
            diffB = bGraph.diff(compGraphBase)

            diffANewTriples = self._accumulate_triples(diffA[1])
            diffBNewTriples = self._accumulate_triples(diffB[1])
            diffARemovedTriples = self._accumulate_triples(diffA[0])
            diffBRemovedTriples = self._accumulate_triples(diffB[0])
            baseTriples = self._get_triples(compGraphBase)
            merged = ((baseTriples - diffARemovedTriples - diffBRemovedTriples) |
                      diffANewTriples | diffBNewTriples)
        else:
            diff = aGraph.diff(bGraph)
            merged = self._get_triples(aGraph)
            merged = merged.union(self._accumulate_triples(diff[0]))

        colourMap = {**(compGraphBase.getBNodeColourMap()),
                     **(bGraph.getBNodeColourMap()),
                     **(aGraph.getBNodeColourMap())}
        colourToNameMap = self._create_colour_to_name_map(colourMap, parserGraphA._bnode_ids,
                                                          parserGraphB._bnode_ids, nameNodeBaseMap)
        merged = self._serialize_triple_sets(merged, colourMap, colourToNameMap)
        blob = self._repository.create_blob(("\n".join(merged) + "\n").encode("utf-8"))

        return blob

    def _accumulate_triples(self, setOfGraphs):
        result = set()
        for aGraph in setOfGraphs:
            result = result.union(self._get_triples(aGraph))
        return result

    def _get_triples(self, graph):
        return set(graph.triples((None, None, None)))

    def _serialize_triple_sets(self, tripleSet, colourMap, colourToNameMap):
        result = set()
        for triple in tripleSet:
            result.add("{} {} {} .".format(self._serialize_bNode(triple[0],
                                                                 colourMap, colourToNameMap),
                                           triple[1].n3(),
                                           self._serialize_bNode(triple[2],
                                                                 colourMap,
                                                                 colourToNameMap)))
        return sorted(result)

    def _serialize_bNode(self, node, colourMap, colourToNameMap):
        if(isinstance(node, rdflib.BNode)):
            try:
                return colourToNameMap[colourMap[node]]
            except KeyError:
                return node.n3()
        else:
            return node.n3()

    def _create_colour_to_name_map(self, nodeColourMap, nameNodeMapA,
                                   nameNodeMapB, nameNodeMapC=None):
        colourToNameMap = {}
        for bNodeName in nameNodeMapA:
            colourKey = nodeColourMap[nameNodeMapA[bNodeName]]
            if colourKey not in colourToNameMap or bNodeName < colourToNameMap[colourKey]:
                colourToNameMap[colourKey] = "_:{}".format(bNodeName)

        for bNodeName in nameNodeMapB:
            bNode = nameNodeMapB[bNodeName]
            colourKey = nodeColourMap[bNode]
            # check if the first two loops already took the label
            unusedCheck = bNodeName not in nameNodeMapA
            if colourKey not in colourToNameMap:
                if unusedCheck:
                    colourToNameMap[colourKey] = "_:{}".format(bNodeName)
                else:
                    colourToNameMap[colourKey] = bNode.n3()
            if bNodeName < colourToNameMap[colourKey] and unusedCheck:
                colourToNameMap[colourKey] = "_:{}".format(bNodeName)

        if nameNodeMapC is not None:
            for bNodeName in nameNodeMapB:
                bNode = nameNodeMapB[bNodeName]
                colourKey = nodeColourMap[bNode]
                # check if the first two loops already took the label
                unusedCheck = bNodeName not in nameNodeMapA and bNodeName not in nameNodeMapB
                if colourKey not in colourToNameMap:
                    if unusedCheck:
                        colourToNameMap[colourKey] = "_:{}".format(bNodeName)
                    else:
                        colourToNameMap[colourKey] = bNode.n3()
                if bNodeName < colourToNameMap[colourKey] and unusedCheck:
                    colourToNameMap[colourKey] = "_:{}".format(bNodeName)

        return colourToNameMap

    def _merge_context_graph_blobs(self, graphAOid, graphBOid, graphBaseOid):
        graphA = comp_graph.ComparableGraph()
        parserGraphA = ntriples.W3CNTriplesParser(ntriples.NTGraphSink(graphA))
        if not str(graphAOid) == pygit2.GIT_OID_HEX_ZERO:
            graphAblob = self._repository[graphAOid].data
            source = rdflib.parser.create_input_source(data=graphAblob.decode("utf-8"))
            parserGraphA.parse(source.getCharacterStream())

        graphB = comp_graph.ComparableGraph()
        parserGraphB = ntriples.W3CNTriplesParser(ntriples.NTGraphSink(graphB))
        if not str(graphBOid) == pygit2.GIT_OID_HEX_ZERO:
            graphBblob = self._repository[graphBOid].data
            source = rdflib.parser.create_input_source(data=graphBblob.decode("utf-8"))
            parserGraphB.parse(source.getCharacterStream())

        nameNodeBaseMap = None
        if graphBaseOid is not None:
            graphBaseblob = self._repository[graphBaseOid].data
            graphBase = comp_graph.ComparableGraph()
            parserGraphBase = ntriples.W3CNTriplesParser(ntriples.NTGraphSink(graphBase))
            source = rdflib.parser.create_input_source(data=graphBaseblob.decode("utf-8"))
            parserGraphBase.parse(source.getCharacterStream())
            nameNodeBaseMap = parserGraphBase._bnode_ids
        else:
            graphBase = comp_graph.ComparableGraph()

        diffA = graphA.diff(graphBase)
        diffB = graphB.diff(graphBase)

        colourMap = {**(graphBase.getBNodeColourMap()),
                     **(graphB.getBNodeColourMap()),
                     **(graphA.getBNodeColourMap())}
        colourToNameMap = self._create_colour_to_name_map(colourMap, parserGraphA._bnode_ids,
                                                          parserGraphB._bnode_ids, nameNodeBaseMap)

        # those operations are not ready since they actually need to be done by their colour
        diffANewTriples = self._accumulate_triples(diffA[1])  # C+c
        diffANewTriples = self._colour_triple_sets(diffANewTriples, colourMap)
        diffBNewTriples = self._accumulate_triples(diffB[1])  # C+b
        diffBNewTriples = self._colour_triple_sets(diffBNewTriples, colourMap)
        diffARemovedTriples = self._accumulate_triples(diffA[0])  # C-c
        diffARemovedTriples = self._colour_triple_sets(diffARemovedTriples, colourMap)
        diffBRemovedTriples = self._accumulate_triples(diffB[0])  # C-b
        diffBRemovedTriples = self._colour_triple_sets(diffBRemovedTriples, colourMap)
        baseTriples = self._get_triples(graphBase)
        baseTriples = self._colour_triple_sets(baseTriples, colourMap)
        ok, conflicts = self._merge_context_conflict_detection(diffANewTriples, diffARemovedTriples,
                                                               diffBNewTriples, diffBRemovedTriples,
                                                               colourToNameMap)

        merged = baseTriples - diffARemovedTriples - diffBRemovedTriples  # P(G') ^ P(G'')
        merged = self._convert_colour_to_name_triple_rows(merged, colourToNameMap)
        merged = merged.union(ok)

        if conflicts is not None:
            raise QuitBlobMergeConflict("Conflicts, ahhhh", merged, conflicts)

        blob = self._repository.create_blob("\n".join(merged).encode("utf-8"))
        return blob

    def _merge_context_conflict_detection(self, addA, delA, addB, delB, colNameMap):

        def conflictSet(tripleSet, conflictingNodes, colNameMap):
            ok = set()
            conflicts = set()
            for triple in tripleSet:
                conflicted = triple[0] in conflictingNodes or triple[2] in conflictingNodes
                if isinstance(triple[0], bytes):
                    subject = colNameMap[triple[0]]
                else:
                    subject = triple[0].n3()

                if isinstance(triple[2], bytes):
                    object = colNameMap[triple[2]]
                elif isinstance(triple[2], rdflib.Literal):
                    object = _qLiteral(triple[2])
                else:
                    object = triple[2].n3()

                cTriple = ("%s %s %s .\n" % (subject, triple[1].n3(), object)).rstrip()
                if conflicted:
                    conflicts.add(cTriple)
                else:
                    ok.add(cTriple)
            return ok, conflicts

        def collectNodes(tripleSet):
            nodes = set()
            for triple in tripleSet:
                nodes.add(triple[0])
                nodes.add(triple[2])
            return nodes

        addANoB = addA - addB  # C+c\b
        addANoBNodes = collectNodes(addANoB)
        addBNoA = addB - addA  # C+b\c
        addBNoANodes = collectNodes(addBNoA)
        delANoB = delA - delB  # C-c\b
        delANoBNodes = collectNodes(delANoB)
        delBNoA = delB - delA  # C-b\c
        delBNoANodes = collectNodes(delBNoA)

        conflictingNodes = (addANoBNodes | delANoBNodes).intersection(addBNoANodes | delBNoANodes)
        logger.debug(conflictingNodes)

        conflicts = {}
        ok = set()

        for key, graph in [("addA", addANoB), ("delA", delANoB),
                           ("addB", addBNoA), ("delB", delBNoA)]:
            newOK, conflict = conflictSet(graph, conflictingNodes, colNameMap)
            if len(conflict) > 0:
                conflicts[key] = "\n".join(sorted(conflict))
            if key.startswith("add"):
                ok.update(newOK)

        if conflicts:
            nodes = []
            for node in conflictingNodes:
                logger.debug(node.n3())
                if isinstance(node, bytes):
                    nodes.append(colNameMap[node])
                else:
                    nodes.append(node.n3())
            conflicts["nodes"] = nodes

        return sorted(ok), conflicts or None

    def _colour_triple_sets(self, tripleSet, colourMap):
        result = set()
        for triple in tripleSet:
            subject = triple[0]
            object = triple[2]
            if isinstance(triple[0], rdflib.BNode) or isinstance(triple[0], rdflib.term.BNode):
                subject = colourMap[triple[0]]
            if isinstance(triple[2], rdflib.BNode) or isinstance(triple[2], rdflib.term.BNode):
                object = colourMap[triple[2]]
            result.add((subject, triple[1], object))
        return result

    def _convert_colour_to_name_triple_rows(self, tripleSet, colNameMap):
        result = set()
        for triple in tripleSet:
            if isinstance(triple[0], bytes):
                subject = colNameMap[triple[0]]
            else:
                subject = triple[0].n3()

            if isinstance(triple[2], bytes):
                object = colNameMap[triple[2]]
            elif isinstance(triple[2], rdflib.Literal):
                object = _qLiteral(triple[2])
            else:
                object = triple[2].n3()

            cTriple = ("%s %s %s .\n" % (subject, triple[1].n3(), object)).rstrip()
            result.add(cTriple)
        return result
