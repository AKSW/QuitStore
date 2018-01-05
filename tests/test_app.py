from context import quit
import os

from distutils.dir_util import copy_tree, remove_tree
from glob import glob
from os import remove, stat, path
from os.path import join, isdir
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Repository, Signature, init_repository
import quit.quit as quitApp
from quit.web.app import create_app
import tempfile
import unittest
import json
from helpers import TemporaryRepository, TemporaryRepositoryFactory
from helpers import createCommit

class QuitAppTestCase(unittest.TestCase):

    author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
    comitter = Signature('QuitStoreTest', 'quit@quit.aksw.org')

    def setUp(self):
        return

    def tearDown(self):
        return

    def testRepoDataAfterInitWithNonEmptyGraph(self):
        """Test file content from newly created app, starting with a non empty graph/repository.

        1. Prepare a git repository with a non empty graph
        2. Start Quit
        3. check file content
        """
        # Prepate a git Repository
        with TemporaryRepositoryFactory().withGraph('urn:graph') as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # get commit message
            for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
                self.assertEqual(commit.message, 'init')

            # compare file content
            with open(join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual('', f.read())

    def testRepoDataAfterInitWithEmptyContent(self):
        """Test file content from newly created app, starting with an empty graph.

        1. Prepare a git repository with a non empty graph
        2. Start Quit
        3. check file content
        """
        # Prepate a git Repository
        graphContent = "<urn:x> <urn:y> <urn:z> <urn:graph> ."
        with TemporaryRepositoryFactory().withGraph('urn:graph', graphContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # get commit message
            for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
                self.assertEqual(commit.message, 'init')

            # compare file content
            with open(join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <urn:graph> .', f.read())

    def testRepoDataAfterInsertStaringWithNonEmptyGraph(self):
        """Test inserting data and check the file content, starting with a non empty graph.

        1. Prepare a git repository with an empty graph
        2. Start Quit
        3. execute INSERT DATA query
        4. check file content
        """
        # Prepate a git Repository
        graphContent = "<urn:x> <urn:y> <urn:z> <urn:graph> ."
        with TemporaryRepositoryFactory().withGraph("urn:graph", graphContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute INSERT DATA query
            update = "INSERT DATA {graph <urn:graph> {<urn:x2> <urn:y2> <urn:z2> .}}"
            app.post('/sparql', data=dict(query=update))

            # test file content
            expectedFileContent = '<urn:x2> <urn:y2> <urn:z2> <urn:graph> .\n'
            expectedFileContent += '<urn:x> <urn:y> <urn:z> <urn:graph> .'

            with open(join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual(expectedFileContent, f.read())

            # check commit messages
            expectedCommitMsg = 'query: INSERT DATA {graph <urn:graph>'
            expectedCommitMsg += ' {<urn:x2> <urn:y2> <urn:z2> .}}\n\nNew Commit from QuitStore'

            commits = []

            for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
                commits.append(commit.message)

            self.assertEqual(commits, [expectedCommitMsg, 'init'])

    def testRepoDataAfterInsertStaringWithEmptyGraph(self):
        """Test inserting data and check the file content, starting with an empty graph.

        1. Prepare a git repository with an empty graph
        2. Start Quit
        3. execute INSERT DATA query
        4. check file content
        """
        # Prepate a git Repository
        with TemporaryRepositoryFactory().withEmptyGraph("urn:graph") as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute INSERT DATA query
            update = "INSERT DATA {graph <urn:graph> {<urn:x> <urn:y> <urn:z> .}}"
            app.post('/sparql', data=dict(query=update))

            # test file content
            expectedFileContent = '<urn:x> <urn:y> <urn:z> <urn:graph> .'

            with open(join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual(expectedFileContent, f.read())

            # check commit messages
            expectedCommitMsg = 'query: INSERT DATA {graph <urn:graph>'
            expectedCommitMsg += ' {<urn:x> <urn:y> <urn:z> .}}\n\nNew Commit from QuitStore'

            commits = []

            for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
                commits.append(commit.message)

            self.assertEqual(commits, [expectedCommitMsg, 'init'])

    def testContentNegotiation(self):
        """Test SPARQL with different Accept Headers."""
        # Prepate a git Repository
        with TemporaryRepositoryFactory().withEmptyGraph("urn:graph") as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles', '-f', 'provenance'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            query = 'SELECT * WHERE {graph ?g {?s ?p ?o .}} LIMIT 1'
            construct = 'CONSTRUCT {?s ?p ?o} WHERE {graph ?g {?s ?p ?o .}} LIMIT 1'

            test_values = {
                'sparql': [query, {
                        '*/*': 'application/sparql-results+xml',
                        'application/sparql-results+xml': 'application/sparql-results+xml',
                        'application/xml': 'application/xml',
                        'application/rdf+xml': 'application/rdf+xml',
                        'application/json': 'application/json',
                        'application/sparql-results+json': 'application/sparql-results+json',
                        'text/csv': 'text/csv',
                        'text/html': 'text/html',
                        'application/xhtml+xml': 'application/xhtml+xml'
                    }
                ],
                'construct': [construct, {
                        '*/*': 'text/turtle',
                        'text/turtle': 'text/turtle',
                        'application/x-turtle': 'application/x-turtle',
                        'application/rdf+xml': 'application/rdf+xml',
                        'application/xml': 'application/xml',
                        'application/n-triples': 'application/n-triples',
                        'application/trig': 'application/trig'
                    }
                ]
            }

            for ep_path in ['/sparql', '/provenance']:
                for query_type, values in test_values.items():
                    query = values[0]

                    # test supported
                    for accept_type, content_type in values[1].items():
                        response = app.post(
                            ep_path,
                            data=dict(query=query),
                            headers={'Accept': accept_type}
                        )
                        self.assertEqual(response.status, '200 OK')
                        self.assertEqual(response.headers['Content-Type'], content_type)

                    # test unsupported
                    resp = app.post(ep_path, data=dict(query=query), headers={'Accept': 'foo/bar'})
                    self.assertEqual(resp.status, '406 NOT ACCEPTABLE')

    def testStartApp(self):
        """Test start of quit store."""
        # Prepate a git Repository
        with TemporaryRepository() as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"
            response = app.post('/sparql', data=dict(query=query))
            self.assertEqual(response.status, '200 OK')

            response = app.post('/provenance', data=dict(query=query))
            self.assertEqual(response.status, '404 NOT FOUND')

    def testFeatureProvenance(self):
        """Test if feature is active or not."""
        # Prepate a git Repository
        with TemporaryRepository() as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles', '-f', 'provenance'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"
            response = app.post('/provenance', data=dict(query=query))
            self.assertEqual(response.status, '200 OK')

    def testReloadStore(self):
        """Test reload of quit store, starting with an emtpy graph.

        1. Start app
        2. Execute INSERT query
        3. Restart app
        4. Execute SELECT query and expect one result
        """
        # Prepate a git Repository
        with TemporaryRepositoryFactory().withEmptyGraph("urn:graph") as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute INSERT DATA query
            update = "INSERT DATA {graph <urn:graph> {<urn:x> <urn:y> <urn:z> .}}"
            app.post('/sparql', data=dict(query=update))

            # reload the store
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            newApp = create_app(config).test_client()

            # execute SELECT query
            select = "SELECT * WHERE {graph <urn:graph> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = newApp.post(
                '/sparql',
                data=dict(query=select),
                headers=dict(accept="application/sparql-results+json")
            )

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

    def testLogfileExists(self):
        """Test if a logfile is created."""
        with TemporaryRepositoryFactory().withEmptyGraph("urn:graph") as repo:
            logFile = join(repo.workdir, 'quit.log')
            self.assertFalse(os.path.isfile(logFile))

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles', '-l', logFile])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            self.assertTrue(os.path.isfile(logFile))

    def testLogfileNotExists(self):
        """Test start of quit store without logfile."""
        with TemporaryRepositoryFactory().withEmptyGraph("urn:graph") as repo:
            logFile = join(repo.workdir, 'quit.log')
            self.assertFalse(os.path.isfile(logFile))

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            self.assertFalse(os.path.isfile(logFile))

    def testCommits(self):
        """Test /commits API request."""
        with TemporaryRepository() as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            response = app.get('/commits', headers={'Accept': 'application/json'})
            self.assertEqual(response.status, '200 OK')
            responseData = json.loads(response.data.decode("utf-8"))
            self.assertListEqual(responseData, [])

            response = app.get('/commits')
            self.assertEqual(response.status, '200 OK')

            response = app.get('/commits', headers={'Accept': 'text/html'})
            self.assertEqual(response.status, '200 OK')

            response = app.get('/commits', headers={'Accept': 'test/nothing'})
            self.assertEqual(response.status, '406 NOT ACCEPTABLE')

            # Create graph with content and commit
            graphContent = "<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."
            with open(join(repo.workdir, "graph.nq"), "w") as graphFile:
                graphFile.write(graphContent)

            with open(path.join(repo.workdir, "graph.nq.graph"), "w") as graphFile:
                graphFile.write('http://example.org')

            createCommit(repository=repo)

            # go on with tests
            response = app.get('/commits', headers={'Accept': 'application/json'})
            self.assertEqual(response.status, '200 OK')
            responseData = json.loads(response.data.decode("utf-8"))
            self.assertEqual(len(responseData), 1)

            response = app.get('/commits', headers={'Accept': 'text/html'})
            self.assertEqual(response.status, '200 OK')

    def testInitAndSelectFromEmptyGraph(self):
        """Test select from newly created app, starting with an empty graph.

        1. Prepare a git repository with an empty graph
        2. Start Quit
        3. execute SELECT query
        """

        # Prepate a git Repository
        with TemporaryRepositoryFactory().withEmptyGraph("http://example.org/") as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp = app.post(
                '/sparql',
                data=dict(query=select),
                headers=dict(accept="application/sparql-results+json")
            )

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 0)

    def testInitAndSelectFromNonEmptyGraph(self):
        """Test select from newly created app, starting with a non empty graph.

        1. Prepare a git repository with a non empty graph
        2. Start Quit
        3. execute SELECT query
        """

        # Prepate a git Repository
        graphContent = "<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post(
                '/sparql',
                data=dict(query=select),
                headers=dict(accept="application/sparql-results+json")
            )

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            # obj = json.load(select_resp.data)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/x'},
                "p": {'type': 'uri', 'value': 'http://ex.org/y'},
                "o": {'type': 'uri', 'value': 'http://ex.org/z'}})

    def testInsertDataAndSelectFromEmptyGraph(self):
        """Test inserting data and selecting it, starting with an empty graph.

        1. Prepare a git repository with an empty graph
        2. Start Quit
        3. execute INSERT DATA query
        4. execute SELECT query
        """

        # Prepate a git Repository
        with TemporaryRepositoryFactory().withEmptyGraph("http://example.org/") as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute INSERT DATA query
            update = "INSERT DATA {graph <http://example.org/> {<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> .}}"
            app.post('/sparql', data=dict(query=update))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            obj = json.loads(select_resp.data.decode("utf-8"))

            try:
                assert len(obj["results"]["bindings"]) == 1
            except AssertionError as e:
                e.args += ('It was expected, that the graph contains 1 (one) statement.', select_resp.data.decode("utf-8"))
                raise

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/a'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})

    def testInsertDataAndSelectFromNonEmptyGraph(self):
        """Test inserting data and selecting it, starting with a non empty graph.

        1. Prepare a git repository with a non empty graph
        2. Start Quit
        3. execute INSERT DATA query
        4. execute SELECT query
        """

        # Prepate a git Repository
        graphContent = "<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute INSERT DATA query
            update = "INSERT DATA {graph <http://example.org/> {<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> .}}"
            app.post('/sparql', data=dict(query=update))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            obj = json.loads(select_resp.data.decode("utf-8"))

            try:
                assert len(obj["results"]["bindings"]) == 2
            except AssertionError as e:
                e.args += ('It was expected, that the graph contains 2 (two) statement.', select_resp.data.decode("utf-8"))
                raise

            # obj = json.load(select_resp.data)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/a'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})


if __name__ == '__main__':
    unittest.main()
