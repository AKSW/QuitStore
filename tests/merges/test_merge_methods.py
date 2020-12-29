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
        """Test merging two commits.  Method: Three-Way"""
        testPath = os.path.dirname(os.path.abspath(__file__))
        for d in listdir(testPath):
            if d[0:4] == "Test" and isdir(join(testPath, d)):
                self._merge_test(join(testPath, d), "three-way")

    def testContextMerge(self):
        """Test merging two commits. Method: Context"""
        testPath = os.path.dirname(os.path.abspath(__file__))
        exceptions = ["TestHouseMerge"]  # TestHouse actually raises a merge conflict exception
        for d in listdir(testPath):
            if d[0:4] == "Test" and isdir(join(testPath, d)) and d not in exceptions:
                self._merge_test(join(testPath, d), "context")

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
                for aControllGraphContent in aControllGraphContents:
                    graph = rdflib.Graph().parse(data=aControllGraphContent, format="nt")
                    for aGraph in aGraphFactory(graph):
                        message = "Merge test {}:\n    Graph {} is not in the set: {}"
                        resultSetString = {a.__hash__() for a in aResultGraphs}
                        message = message.format(dirPath, aGraph.__hash__(), resultSetString)
                        self.assertTrue(aGraph in aResultGraphs, message)
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


if __name__ == '__main__':
    unittest.main()
