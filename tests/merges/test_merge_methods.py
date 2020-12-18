from context import quit

import quit.application as quitApp
from quit.web.app import create_app
import unittest
import pygit2
from helpers import TemporaryRepositoryFactory


class GraphMergeTests(unittest.TestCase):
    """Test if two graphs on differen branches are correctly merged."""

    def setUp(self):
        return

    def tearDown(self):
        return

    def testThreeWayMerge(self):
        """Test merging two commits."""

        # Prepate a git Repository
        file = open("base.nt", "r")
        content = file.read()
        file.close()
        with TemporaryRepositoryFactory().withGraph("http://example.org/", content) as repo:

            def expand_branch(branch, graphFile):
                reference = repo.lookup_reference('refs/heads/%s' % branch)
                branchOid = reference.resolve().target
                branchCommit = repo.get(branchOid)
                treeBuilder = repo.TreeBuilder(branchCommit.tree)
                file = open(graphFile, "r")
                treeBuilder.insert("graph.nt", repo.create_blob(file.read().encode()), 33188)
                file.close()
                treeOID = treeBuilder.write()
                author = pygit2.Signature("test", "test@example.org")
                newCommitOid = repo.create_commit("refs/heads/componentB", author, author,
                                                  "this is a test", treeOID, [branchOid])
                repo.state_cleanup()
                return newCommitOid
            # Start Quit
            args = quitApp.getDefaults()
            args['targetdir'] = repo.workdir
            app = create_app(args).test_client()

            app.post("/branch", data={"oldbranch": "master", "newbranch": "componentA"})
            app.post("/branch", data={"oldbranch": "master", "newbranch": "componentB"})

            expand_branch("componentA", "branch.nt")
            expand_branch("componentB", "target.nt")

            app = create_app(args).test_client()
            app.post("/merge", data={"target": "componentB", "branch": "componentA",
                                     "method": "three-way"})

            reference = repo.lookup_reference('refs/heads/%s' % "componentB")
            branchOid = reference.resolve().target
            branchCommit = repo.get(branchOid)
            file = open("result.nt", "r")
            self.assertEqual(branchCommit.tree["graph.nt"].data.decode("utf-8"),
                             file.read())

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
