#!/usr/bin/env python3
import unittest
from context import quit

import quit.application as quitApp
from quit.web.app import create_app
from tempfile import TemporaryDirectory
from pygit2 import config as gitconfig
import json

class EndpointTests(unittest.TestCase):
    """Test endpoint features."""

    def setUp(self):
        return

    def tearDown(self):
        return

    def testInsertDataNoSnapshotIsolation(self):
        """Test inserting data without checking the snapshot isolation using the commit id.
        """
        # Prepate a git Repository
        with TemporaryDirectory() as repo:

            # Start Quit
            args = quitApp.getDefaults()
            args['targetdir'] = repo
            app = create_app(args).test_client()


            # execute INSERT DATA query
            update = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> a <http://ex.org/Todo> ;
                  <http://ex.org/task> "Take out the organic waste" .
            }}
            """
            response = app.post('/sparql', data=dict(update=update))
            self.assertEqual(response.status_code, 200)

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(select_resp.status_code, 200)

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(select_resp.status_code, 200)

            # execute INSERT DATA query
            update = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> <http://ex.org/status> <http://ex.org/completed> .
            }}
            """
            response = app.post('/sparql', data=dict(update=update))
            self.assertEqual(response.status_code, 200)

            # execute INSERT DATA query
            update = """DELETE {
            GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> ?task .
            }}
            INSERT {
            GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> "Take out the organic waste and the residual waste" .
            }}
            WHERE {
              BIND ("Take out the organic waste" as ?task)
              GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> ?task
              }
            }
            """
            response = app.post('/sparql', data=dict(update=update))
            self.assertEqual(response.status_code, 200)

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(select_resp.status_code, 200)

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 3)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://ex.org/status'},
                "o": {'type': 'uri', 'value': 'http://ex.org/completed'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://ex.org/task'},
                "o": {'type': 'literal', 'value': 'Take out the organic waste and the residual waste'}})
            self.assertDictEqual(obj["results"]["bindings"][2], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                "o": {'type': 'uri', 'value': 'http://ex.org/Todo'}})


    def testInsertDataOverlappingWithReject(self):
        """Test inserting data from two clients (simulated) with overlapping update requests.
        """
        # Prepate a git Repository
        with TemporaryDirectory() as repo:

            # Start Quit
            args = quitApp.getDefaults()
            args['targetdir'] = repo
            app = create_app(args).test_client()

            # execute INSERT DATA query
            update = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> a <http://ex.org/Todo> ;
                  <http://ex.org/task> "Take out the organic waste" .
            }}
            """
            response = app.post('/sparql', data=dict(update=update))
            self.assertEqual(response.status_code, 200)

            # Client A: execute SELECT query
            selectA = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            selectA_resp = app.post('/sparql', data=dict(query=selectA), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(selectA_resp.status_code, 200)
            branchA = selectA_resp.headers['X-CurrentBranch']
            commitA = selectA_resp.headers['X-CurrentCommit']

            # Client B: execute SELECT query
            selectB = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            selectB_resp = app.post('/sparql', data=dict(query=selectB), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(selectB_resp.status_code, 200)
            branchB = selectB_resp.headers['X-CurrentBranch']
            commitB = selectB_resp.headers['X-CurrentCommit']
            self.assertEqual(commitA, commitB)
            self.assertEqual(branchA, branchB)

            # Client B: update operation
            updateB = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> <http://ex.org/status> <http://ex.org/completed> .
            }}
            """
            response = app.post('/sparql', data=dict(update=updateB, parent_commit_id=commitB, resolution_method='reject'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(branchB, response.headers['X-CurrentBranch'])
            self.assertNotEqual(commitB, response.headers['X-CurrentCommit'])

            # Client A: update operation
            updateA = """DELETE {
            GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> ?task .
            }}
            INSERT {
            GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> "Take out the organic waste and the residual waste" .
            }}
            WHERE {
              BIND ("Take out the organic waste" as ?task)
              GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> ?task
              }
            }
            """
            response = app.post('/sparql', data=dict(update=updateA, parent_commit_id=commitA, resolution_method='reject'))
            # FAILURE. The second request should be rejected because it asumes a different commit
            self.assertEqual(response.status_code, 409)

            # check the result
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(select_resp.status_code, 200)
            self.assertEqual(branchA, select_resp.headers['X-CurrentBranch'])
            self.assertNotEqual(commitA, select_resp.headers['X-CurrentCommit'])

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 3)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://ex.org/status'},
                "o": {'type': 'uri', 'value': 'http://ex.org/completed'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://ex.org/task'},
                "o": {'type': 'literal', 'value': 'Take out the organic waste'}})
            self.assertDictEqual(obj["results"]["bindings"][2], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                "o": {'type': 'uri', 'value': 'http://ex.org/Todo'}})


    def testInsertDataOverlappingWithBranch(self):
        """Test inserting data from two clients (simulated) with overlapping update requests and branch resolution
        """
        # Prepate a git Repository
        with TemporaryDirectory() as repo:

            # Start Quit
            args = quitApp.getDefaults()
            args['targetdir'] = repo
            app = create_app(args).test_client()

            # execute INSERT DATA query
            update = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> a <http://ex.org/Todo> ;
                  <http://ex.org/task> "Take out the organic waste" .
            }}
            """
            response = app.post('/sparql', data=dict(update=update))
            self.assertEqual(response.status_code, 200)

            # Client A: execute SELECT query
            selectA = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            selectA_resp = app.post('/sparql', data=dict(query=selectA), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(selectA_resp.status_code, 200)
            branchA = selectA_resp.headers['X-CurrentBranch']
            commitA = selectA_resp.headers['X-CurrentCommit']

            # Client B: execute SELECT query
            selectB = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            selectB_resp = app.post('/sparql', data=dict(query=selectB), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(selectB_resp.status_code, 200)
            branchB = selectB_resp.headers['X-CurrentBranch']
            commitB = selectB_resp.headers['X-CurrentCommit']
            self.assertEqual(commitA, commitB)
            self.assertEqual(branchA, branchB)

            # Client B: update operation
            updateB = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> <http://ex.org/status> <http://ex.org/completed> .
            }}
            """
            response = app.post('/sparql', data=dict(update=updateB, parent_commit_id=commitB, resolution_method='branch'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(branchB, response.headers['X-CurrentBranch'])
            newCommitB = response.headers['X-CurrentCommit']
            self.assertNotEqual(commitB, newCommitB)

            # Client A: update operation
            updateA = """DELETE {
            GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> ?task .
            }}
            INSERT {
            GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> "Take out the organic waste and the residual waste" .
            }}
            WHERE {
              BIND ("Take out the organic waste" as ?task)
              GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> ?task
              }
            }
            """
            response = app.post('/sparql', data=dict(update=updateA, parent_commit_id=commitA, resolution_method='branch'))
            # FAILURE. The second request should be rejected because it asumes a different commit
            self.assertEqual(response.status_code, 200)
            newBranchA = response.headers['X-CurrentBranch']
            self.assertNotEqual(branchA, newBranchA)
            newCommitA = response.headers['X-CurrentCommit']
            self.assertNotEqual(commitA, newCommitA)
            self.assertNotEqual(newCommitB, newCommitA)

            # check the result on the master branch
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(select_resp.status_code, 200)
            self.assertEqual(branchB, select_resp.headers['X-CurrentBranch'])
            self.assertEqual(newCommitB, select_resp.headers['X-CurrentCommit'])

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 3)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://ex.org/status'},
                "o": {'type': 'uri', 'value': 'http://ex.org/completed'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://ex.org/task'},
                "o": {'type': 'literal', 'value': 'Take out the organic waste'}})
            self.assertDictEqual(obj["results"]["bindings"][2], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                "o": {'type': 'uri', 'value': 'http://ex.org/Todo'}})


            # check the result on the newly created branch
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql/{}'.format(newBranchA), data=dict(query=select), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(select_resp.status_code, 200)
            self.assertEqual(newBranchA, select_resp.headers['X-CurrentBranch'])
            self.assertEqual(newCommitA, select_resp.headers['X-CurrentCommit'])

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 2)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://ex.org/task'},
                "o": {'type': 'literal', 'value': 'Take out the organic waste and the residual waste'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                "o": {'type': 'uri', 'value': 'http://ex.org/Todo'}})


    def testInsertDataOverlappingWithMerge(self):
        """Test inserting data from two clients (simulated) with overlapping update requests and merge resolution
        """
        # Prepate a git Repository
        with TemporaryDirectory() as repo:

            # Start Quit
            args = quitApp.getDefaults()
            args['targetdir'] = repo
            app = create_app(args).test_client()

            # execute INSERT DATA query
            update = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> a <http://ex.org/Todo> ;
                  <http://ex.org/task> "Take out the organic waste" .
            }}
            """
            response = app.post('/sparql', data=dict(update=update))
            self.assertEqual(response.status_code, 200)

            # Client A: execute SELECT query
            selectA = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            selectA_resp = app.post('/sparql', data=dict(query=selectA), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(selectA_resp.status_code, 200)
            branchA = selectA_resp.headers['X-CurrentBranch']
            commitA = selectA_resp.headers['X-CurrentCommit']

            # Client B: execute SELECT query
            selectB = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            selectB_resp = app.post('/sparql', data=dict(query=selectB), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(selectB_resp.status_code, 200)
            branchB = selectB_resp.headers['X-CurrentBranch']
            commitB = selectB_resp.headers['X-CurrentCommit']
            self.assertEqual(commitA, commitB)
            self.assertEqual(branchA, branchB)

            # Client B: update operation
            updateB = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> <http://ex.org/status> <http://ex.org/completed> .
            }}
            """
            response = app.post('/sparql', data=dict(update=updateB, parent_commit_id=commitB, resolution_method='merge'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(branchB, response.headers['X-CurrentBranch'])
            newCommitB = response.headers['X-CurrentCommit']
            self.assertNotEqual(commitB, newCommitB)

            # Client A: update operation
            updateA = """DELETE {
            GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> ?task .
            }}
            INSERT {
            GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> "Take out the organic waste and the residual waste" .
            }}
            WHERE {
              BIND ("Take out the organic waste" as ?task)
              GRAPH <http://example.org/> {
                ?todo <http://ex.org/task> ?task
              }
            }
            """
            response = app.post('/sparql', data=dict(update=updateA, parent_commit_id=commitA, resolution_method='merge'))
            # FAILURE. The second request should be rejected because it asumes a different commit
            self.assertEqual(response.status_code, 200)
            self.assertEqual(branchA, response.headers['X-CurrentBranch'])
            newCommitA = response.headers['X-CurrentCommit']
            self.assertNotEqual(commitA, newCommitA)
            self.assertNotEqual(newCommitB, newCommitA)

            # check the result on the master branch
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))
            self.assertEqual(select_resp.status_code, 200)
            self.assertEqual(branchB, select_resp.headers['X-CurrentBranch'])
            self.assertEqual(newCommitA, select_resp.headers['X-CurrentCommit'])

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 3)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://ex.org/status'},
                "o": {'type': 'uri', 'value': 'http://ex.org/completed'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://ex.org/task'},
                "o": {'type': 'literal', 'value': 'Take out the organic waste and the residual waste'}})
            self.assertDictEqual(obj["results"]["bindings"][2], {
                "s": {'type': 'uri', 'value': 'http://ex.org/garbage'},
                "p": {'type': 'uri', 'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                "o": {'type': 'uri', 'value': 'http://ex.org/Todo'}})

    def testInsertDataWithNoGitConfigUser(self):
        with TemporaryDirectory() as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()
            gitGlobalConfig = gitconfig.Config.get_global_config()
            username = gitGlobalConfig["user.name"]
            email = gitGlobalConfig["user.email"]
            try:
                del gitGlobalConfig["user.name"]
                # execute INSERT DATA query
                update = """INSERT DATA {
                GRAPH <http://example.org/> {
                    <http://ex.org/garbage> a <http://ex.org/Todo> ;
                    <http://ex.org/task> "Take out the organic waste" .
                    }}
                    """
                response = app.post('/sparql', data=dict(update=update))
                message = response.get_data().decode("utf-8")
                self.assertEqual(
                    message,
                    ("Unable to process query: git config value 'user.name' "
                     "was not found.\nPlease use the following command in your"
                     " data repo:\n\n  git config user.name <your name>"))
                # Uncommenting the second line below and commenting the first
                # causes the test to fail with an KeyError.
                # "username" and username are both str s
                # Even more, the same code line still correctly reset user.name
                # and user.email
                gitGlobalConfig["user.name"] = username
                del gitGlobalConfig["user.email"]
                response = app.post('/sparql', data=dict(update=update))
                gitGlobalConfig["user.name"] = username
                gitGlobalConfig["user.email"] = email
                message = response.get_data().decode("utf-8")
                self.assertEqual(
                    message,
                    ("Unable to process query: git config value 'user.email' "
                     "was not found.\nPlease use the following command in your"
                     " data repo:\n\n  git config user.email <your email>"))
            except Exception as e:
                gitGlobalConfig["user.name"] = username
                gitGlobalConfig["user.email"] = email
                raise e

if __name__ == '__main__':
    unittest.main()
