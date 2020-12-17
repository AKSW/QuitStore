from context import quit
import os
from os import path

from urllib.parse import quote_plus
from datetime import datetime
from pygit2 import GIT_SORT_TOPOLOGICAL, Signature, GIT_OBJ_BLOB
from quit.conf import Feature
import quit.application as quitApp
from quit.web.app import create_app
import unittest
from helpers import TemporaryRepository, TemporaryRepositoryFactory
import json
from helpers import createCommit, assertResultBindingsEqual
from tempfile import TemporaryDirectory
from quit.utils import iri_to_name


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


            # Start Quit
            args = quitApp.getDefaults()
            args['targetdir'] = repo.workdir
            app = create_app(args).test_client()

            app.post("/branch", data={"oldbranch": "master", "newbranch": "componentA"})
            app.post("/branch", data={"oldbranch": "master", "newbranch": "componentB"})

            # execute INSERT DATA query
            file = open("branch.nt", "r")
            update = "INSERT DATA {graph <http://example.org/> {" + file.read() + "}}"
            app.post('/sparql/componentA?ref=componentA', data={"query": update})
            file.close()

            index = repo.index
            index.read()
            id = index['graph.nt'].id
            blob = repo[id]
            print(blob.data.decode("utf-8"))

            app = create_app(args).test_client()
            # start new app to syncAll()
            file = open("target.nt", "r")
            update = "INSERT DATA {graph <http://example.org/> {" + file.read() + "}}"
            app.post('/sparql/componentB?ref=componentB', data={"query": update})
            file.close()

            #branchTarget = "refs/heads/componentB"
            branchTarget =  "componentB"
            for entry in repo:
                print(entry)
            for branch in repo.branches:
                print(branch)

            reference = repo.lookup_reference('refs/heads/%s' % branchTarget)
            targetOid = reference.resolve().target
            #targetOid = repo.get(branchTarget)
            targetCommit = repo.get(targetOid)
            print(targetCommit)
            #targetCommit.index.read()
            for attr in dir(repo):
                print(attr)
            repo.checkout(targetCommit.refname)
            #print(targetCommit.tree.name)


            app.post("/merge", data={"target": "componentB", "branch": "componentA", "method": "three-way"})

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
