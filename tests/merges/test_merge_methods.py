from context import quit

import os
from os import listdir
from os.path import isfile, isdir, join
import quit.application as quitApp
from quit.web.app import create_app
import unittest
import pygit2
from helpers import TemporaryRepositoryFactory
import rdflib
from atomicgraphs.atomic_graph import AtomicGraphFactory as aGraphFactory


class GraphMergeTests(unittest.TestCase):
    """Test if two graphs on differen branches are correctly merged."""

    def setUp(self):
        return

    def tearDown(self):
        return

    def testThreeWayMerge(self):
        """Test merging two commits."""
        testPath = os.path.dirname(os.path.abspath(__file__))
        # for d in listdir(testPath):
        # for d in ["TestA", "TestHouseMerge", "TestABCD", "TestB", "TestC"]:
        #     if isdir(join(testPath, d)) and d != "__pycache__":
        #         self._merge_test(d, "three-way")
        for d in ["TestD"]:
            if isdir(join(testPath, d)) and d != "__pycache__":
                print("#######################################")
                print("###              {}              ###".format(d))
                print("#######################################")
                self._merge_test(d, "three-way")

    def _merge_test(self, dirPath, method):
        # Prepate a git Repository
        file = open(join(dirPath, "base.nt"), "r")
        content = file.read()
        file.close()
        with TemporaryRepositoryFactory().withGraph("http://example.org/", content) as repo:
            # Start Quit
            args = quitApp.getDefaults()
            args['targetdir'] = repo.workdir
            app = create_app(args).test_client()

            app.post("/branch", data={"oldbranch": "master", "newbranch": "componentA"})
            app.post("/branch", data={"oldbranch": "master", "newbranch": "componentB"})

            self.expand_branch(repo, "componentA", join(dirPath, "branch.nt"))
            self.expand_branch(repo, "componentB", join(dirPath, "target.nt"))

            app = create_app(args).test_client()
            app.post("/merge", data={"target": "componentB", "branch": "componentA",
                                     "method": method})

            reference = repo.lookup_reference('refs/heads/%s' % "componentB")
            branchOid = reference.resolve().target
            branchCommit = repo.get(branchOid)
            if isfile(join(dirPath, "a_graphs")):
                file = open(join(dirPath, "a_graphs"), "r")
                aControllGraphContents = file.read().split("---")
                file.close()
                resultContent = branchCommit.tree["graph.nt"].data.decode("utf-8")
                resultGraph = rdflib.Graph().parse(data=resultContent, format="nt")
                aResultGraphs = set(iter(aGraphFactory(resultGraph)))
                print("ResultContent:\n{}\n-----".format(resultContent))
                print("Current Result Set:\n-->{}".format({a.__hash__() for a in aResultGraphs}))
                for aControllGraphContent in aControllGraphContents:
                    graph = rdflib.Graph().parse(data=aControllGraphContent, format="nt")
                    for aGraph in aGraphFactory(graph):
                        print("aGraph: {}".format(aGraph.__hash__()))
                        message = "Merge test {}:\n    Graph {} is not in the set: {}"
                        resultSetString = {a.__hash__() for a in aResultGraphs}
                        message = message.format(dirPath, aGraph.__hash__(), resultSetString)
                        try:
                            self.assertTrue(aGraph in aResultGraphs, message)
                        except AssertionError:
                            graphFile = open(join(dirPath, "debugResult"), "w")
                            graphFile.write(self.__show_comparison(aGraph, aControllGraphContent))
                            graphFile.close()
                            print("- {}".format(self.__show_colours(next(iter(aResultGraphs)))))
                            print("- {}".format(self.__show_colours(aGraph)))
                            raise
                        aResultGraphs.remove(aGraph)
                message = "Merge test {}:\n    Not all graphs were defined in a_graphs: {}"
                message = message.format(dirPath, aResultGraphs)
                self.assertEqual(0, len(aResultGraphs), message)
            else:
                file = open(join(dirPath, "result.nt"), "r")
                self.assertEqual(branchCommit.tree["graph.nt"].data.decode("utf-8"), file.read())
                file.close()

    def expand_branch(self, repo, branch, graphFile):
        reference = repo.lookup_reference('refs/heads/%s' % branch)
        branchOid = reference.resolve().target
        branchCommit = repo.get(branchOid)
        treeBuilder = repo.TreeBuilder(branchCommit.tree)
        file = open(graphFile, "r")
        treeBuilder.insert("graph.nt", repo.create_blob(file.read().encode()), 33188)
        file.close()
        treeOID = treeBuilder.write()
        author = pygit2.Signature("test", "test@example.org")
        newCommitOid = repo.create_commit("refs/heads/%s" % branch, author, author,
                                          "this is a test", treeOID, [branchOid])
        repo.state_cleanup()
        return newCommitOid

    # TODO remove
    def __show_comparison(self, graph, controllContent):
        listLabel = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]
        bNodeMap = {}
        for triple in graph:
            node = triple[0]
            if node.n3() not in bNodeMap:
                if isinstance(node, rdflib.BNode):
                    bNodeMap[node.n3()] = "_:{}".format(listLabel.pop(0))
                else:
                    bNodeMap[node.n3()] = "<{}>".format(node.n3())
            node = triple[2]
            if node.n3() not in bNodeMap:
                if isinstance(node, rdflib.BNode):
                    bNodeMap[node.n3()] = "_:{}".format(listLabel.pop(0))
                else:
                    bNodeMap[node.n3()] = "<{}>".format(node.n3())
        template = "{1}"
        result = ""
        for triple in graph:
            newLine = "{} <{}> {} .".format(bNodeMap[triple[0].n3()],
                                            triple[1], bNodeMap[triple[2].n3()])
            result = template.format(result, newLine)
            template = "{0}\n{1}"
        return result

    def __show_colours(self, graph):
        bNodeSet = set()
        for triple in graph:
            if isinstance(triple[0], rdflib.BNode):
                bNodeSet.add(triple[0])
            if isinstance(triple[2], rdflib.BNode):
                bNodeSet.add(triple[2])
        colourSet = set(graph.colourPartitions[x] for x in bNodeSet)
        print("===")
        for node in bNodeSet:
            print("node  {}".format(graph.colourPartitions[node]))
        return sorted(colourSet)


#    def testContextMerge(self):
#        """Test merging two commits."""
#
#        # Prepate a git Repository
#        content = "<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> ."
#        with TemporaryRepositoryFactory().withGraph("http://example.org/", content) as repo:
#
#            # Start Quit
#            args = quitApp.getDefaults()
#            args['targetdir'] = repo.workdirdevelop
#            app = create_app(args).test_client()
#
#            app.post("/branch", data={"oldbranch": "master", "newbranch": "develop"})
#
#            # execute INSERT DATA query
#            update = "INSERT DATA {graph <http://example.org/> {<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> .}}"
#            app.post('/sparql', data={"query": update})
#
#            app = create_app(args).test_client()
#            # start new app to syncAll()
#
#            update = "INSERT DATA {graph <http://example.org/> {<http://ex.org/z> <http://ex.org/z> <http://ex.org/z> .}}"
#            app.post('/sparql/develop?ref=develop', data={"query": update})
#
#            app.post("/merge", data={"target": "master", "branch": "develop", "method": "context"})


if __name__ == '__main__':
    unittest.main()
