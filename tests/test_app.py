from context import quit
import os
from os import path

from datetime import datetime
from pygit2 import GIT_SORT_TOPOLOGICAL, Signature
import quit.quit as quitApp
from quit.web.app import create_app
import unittest
from helpers import TemporaryRepository, TemporaryRepositoryFactory
import json
from helpers import createCommit, assertResultBindingsEqual


class QuitAppTestCase(unittest.TestCase):

    author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
    comitter = Signature('QuitStoreTest', 'quit@quit.aksw.org')

    def setUp(self):
        return

    def tearDown(self):
        return

    def testBlame(self):
        """Test if feature responds with correct values.

        1. Prepare a git repository with a non empty graph
        2. Get id of the existing commit
        3. Call /blame/master and /blame/{commitId} with all specified accept headers and test the
           response data
        """
        # Prepate a git Repository
        graphContent = "<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles', '-f', 'provenance'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
                oid = str(commit.id)

            expected = {
                's': {'type': 'uri', 'value': 'http://ex.org/x'},
                'p': {'type': 'uri', 'value': 'http://ex.org/y'},
                'o': {'type': 'uri', 'value': 'http://ex.org/z'},
                'context': {'type': 'uri', 'value': 'http://example.org/'},
                'hex': {'type': 'literal', 'value': oid},
                'name': {'type': 'literal', 'value': 'QuitStoreTest'},
                'email': {'type': 'literal', 'value': 'quit@quit.aksw.org'}
            }

            for apiPath in ['master', oid]:
                response = app.get('/blame/{}'.format(apiPath))
                resultBindings = json.loads(response.data.decode("utf-8"))['results']['bindings']
                results = resultBindings[0]

                self.assertEqual(len(resultBindings), 1)
                # compare expected date separately without time
                self.assertTrue(
                    results['date']['value'].startswith(datetime.now().strftime('%Y-%m-%d'))
                )
                self.assertEqual(
                    results['date']['datatype'], 'http://www.w3.org/2001/XMLSchema#dateTime'
                )
                self.assertEqual(results['date']['type'], 'typed-literal')

                del results['date']

                queryVariables = ['s', 'p', 'o', 'context', 'hex', 'name', 'email']

                # compare lists (without date)
                assertResultBindingsEqual(self, [expected], resultBindings, queryVariables)

    def testBlameApi(self):
        """Test if feature is active or not.

        1. Prepare a git repository with a non empty graph
        2. Get id of the existing commit
        3. Call /blame/master and /blame/{commitId} with all specified accept headers and test the
           response status
        """
        # Prepate a git Repository
        graphContent = "<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles', '-f', 'provenance'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
                oid = str(commit.id)

            graphUri = 'http://example.org/'

            mimetypes = [
                'text/html', 'application/xhtml_xml', '*/*',
                'application/json', 'application/sparql-results+json',
                'application/rdf+xml', 'application/xml', 'application/sparql-results+xml',
                'application/csv', 'text/csv'
            ]

            # Test API with existing paths and specified accept headers
            for apiPath in ['master', oid]:
                for header in mimetypes:
                    response = app.get('/blame/{}'.format(apiPath), headers={'Accept': header})
                    self.assertEqual(response.status, '200 OK')

            # Test API default accept header
            response = app.get('/blame/master')
            self.assertEqual(response.status, '200 OK')

            # Test API with not acceptable header
            response = app.get('/blame/foobar', headers={'Accept': 'foo/bar'})
            self.assertEqual(response.status, '400 BAD REQUEST')

            # Test API with non existing path
            response = app.get('/blame/foobar')
            self.assertEqual(response.status, '400 BAD REQUEST')

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
            with open(path.join(repo.workdir, "graph.nq"), "w") as graphFile:
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

            query = "foo bar"
            response = app.post('/provenance', data=dict(query=query))
            self.assertEqual(response.status, '400 BAD REQUEST')

            query = "INSERT DATA {graph <urn:graph> {<urn:x> <urn:y> <urn:z> .}}"
            response = app.post('/provenance', data=dict(query=query))
            self.assertEqual(response.status, '400 BAD REQUEST')

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

            self.assertEqual(len(obj["results"]["bindings"]), 1)

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

            self.assertEqual(len(obj["results"]["bindings"]), 2)

            # obj = json.load(select_resp.data)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/a'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})

    def testLogfileExists(self):
        """Test if a logfile is created."""
        with TemporaryRepositoryFactory().withEmptyGraph("urn:graph") as repo:
            logFile = path.join(repo.workdir, 'quit.log')
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
            logFile = path.join(repo.workdir, 'quit.log')
            self.assertFalse(os.path.isfile(logFile))

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            self.assertFalse(os.path.isfile(logFile))

    def testThreeWayMerge(self):
        """Test merging two commits."""

        # Prepate a git Repository
        content = "<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> <http://example.org/> ."
        with TemporaryRepositoryFactory().withGraph("http://example.org/", content) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles', '-vv'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            app.post("/branch", data={"oldbranch": "master", "newbranch": "develop"})

            # execute INSERT DATA query
            update = "INSERT DATA {graph <http://example.org/> {<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> .}}"
            app.post('/sparql', data={"query": update})

            app = create_app(config).test_client()
            # start new app to syncAll()
            # Otherwise the next update query would have created unassigend.nq

            update = "INSERT DATA {graph <http://example.org/> {<http://ex.org/z> <http://ex.org/z> <http://ex.org/z> .}}"
            app.post('/sparql/develop?ref=develop', data={"query": update})

            app.post("/merge", data={"target": "master", "branch": "develop", "method": "three-way"})

    def testContextMerge(self):
        """Test merging two commits."""

        # Prepate a git Repository
        content = "<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> <http://example.org/> ."
        with TemporaryRepositoryFactory().withGraph("http://example.org/", content) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles', '-vv'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            app.post("/branch", data={"oldbranch": "master", "newbranch": "develop"})

            # execute INSERT DATA query
            update = "INSERT DATA {graph <http://example.org/> {<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> .}}"
            app.post('/sparql', data={"query": update})

            app = create_app(config).test_client()
            # start new app to syncAll()
            # Otherwise the next update query would have created unassigend.nq

            update = "INSERT DATA {graph <http://example.org/> {<http://ex.org/z> <http://ex.org/z> <http://ex.org/z> .}}"
            app.post('/sparql/develop?ref=develop', data={"query": update})

            app.post("/merge", data={"target": "master", "branch": "develop", "method": "context"})

    def testPull(self):
        """Test /pull API request."""
        graphContent = """
            <http://ex.org/x> <http://ex.org/x> <http://ex.org/x> <http://example.org/> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryRepository(clone_from_repo=remote) as local:

                with open(path.join(remote.workdir, "graph.nq"), "a") as graphFile:
                    graphContent = """
                        <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."""
                    graphFile.write(graphContent)

                createCommit(repository=remote)

                args = quitApp.parseArgs(['-t', local.workdir, '-cm', 'graphfiles'])
                objects = quitApp.initialize(args)

                config = objects['config']
                app = create_app(config).test_client()

                beforePull = {'s': {'type': 'uri', 'value': 'http://ex.org/x'},
                              'p': {'type': 'uri', 'value': 'http://ex.org/x'},
                              'o': {'type': 'uri', 'value': 'http://ex.org/x'},
                              'g': {'type': 'uri', 'value': 'http://example.org/'}}

                query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"

                response = app.post('/sparql', data=dict(query=query),
                                    headers={'Accept': 'application/sparql-results+json'})
                resultBindings = json.loads(response.data.decode("utf-8"))['results']['bindings']

                self.assertEqual(len(resultBindings), 1)
                self.assertDictEqual(resultBindings[0], beforePull)
                assertResultBindingsEqual(self, resultBindings, [beforePull])

                response = app.get('/pull/origin')
                self.assertEqual(response.status, '200 OK')

                afterPull = {'s': {'type': 'uri', 'value': 'http://ex.org/x'},
                             'p': {'type': 'uri', 'value': 'http://ex.org/y'},
                             'o': {'type': 'uri', 'value': 'http://ex.org/z'},
                             'g': {'type': 'uri', 'value': 'http://example.org/'}}

                response = app.post('/sparql', data=dict(query=query),
                                    headers={'Accept': 'application/sparql-results+json'})
                resultBindings = json.loads(response.data.decode("utf-8"))['results']['bindings']

                self.assertEqual(response.status, '200 OK')
                self.assertEqual(len(resultBindings), 2)

                assertResultBindingsEqual(self, resultBindings, [beforePull, afterPull])

    def testPullEmptyInitialGraph(self):
        """Test /pull API request starting with an initially empty graph."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", "") as remote:
            with TemporaryRepository(clone_from_repo=remote) as local:

                with open(path.join(remote.workdir, "graph.nq"), "a") as graphFile:
                    graphContent = """
                        <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."""
                    graphFile.write(graphContent)

                createCommit(repository=remote)

                args = quitApp.parseArgs(['-t', local.workdir, '-cm', 'graphfiles'])
                objects = quitApp.initialize(args)

                config = objects['config']
                app = create_app(config).test_client()

                query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"

                response = app.post('/sparql', data=dict(query=query),
                                    headers={'Accept': 'application/sparql-results+json'})
                resultBindings = json.loads(response.data.decode("utf-8"))['results']['bindings']

                self.assertEqual(len(resultBindings), 0)
                assertResultBindingsEqual(self, resultBindings, [])

                response = app.get('/pull/origin')
                self.assertEqual(response.status, '200 OK')

                afterPull = {'s': {'type': 'uri', 'value': 'http://ex.org/x'},
                             'p': {'type': 'uri', 'value': 'http://ex.org/y'},
                             'o': {'type': 'uri', 'value': 'http://ex.org/z'},
                             'g': {'type': 'uri', 'value': 'http://example.org/'}}

                response = app.post('/sparql', data=dict(query=query),
                                    headers={'Accept': 'application/sparql-results+json'})
                resultBindings = json.loads(response.data.decode("utf-8"))['results']['bindings']

                self.assertEqual(response.status, '200 OK')
                self.assertEqual(len(resultBindings), 1)

                assertResultBindingsEqual(self, resultBindings, [afterPull])

    @unittest.skip("See https://github.com/AKSW/QuitStore/issues/81")
    def testPullStartFromEmptyRepository(self):
        """Test /pull API request starting the store from an empty repository.

        CAUTION: This test is disabled, because we currently have problems starting a store when no
        graph is configured. See https://github.com/AKSW/QuitStore/issues/81
        """
        graphContent = """
            <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryRepository() as local:
                local.remotes.create("origin", remote.path)

                args = quitApp.parseArgs(['-t', local.workdir, '-cm', 'graphfiles'])
                objects = quitApp.initialize(args)

                config = objects['config']
                app = create_app(config).test_client()

                query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"

                response = app.post('/sparql', data=dict(query=query),
                                    headers={'Accept': 'application/sparql-results+json'})
                resultBindings = json.loads(response.data.decode("utf-8"))['results']['bindings']

                self.assertEqual(len(resultBindings), 0)

                response = app.get('/pull/origin')
                self.assertEqual(response.status, '200 OK')

                afterPull = {'s': {'type': 'uri', 'value': 'http://ex.org/x'},
                             'p': {'type': 'uri', 'value': 'http://ex.org/y'},
                             'o': {'type': 'uri', 'value': 'http://ex.org/z'},
                             'g': {'type': 'uri', 'value': 'http://example.org/'}}

                response = app.post('/sparql', data=dict(query=query),
                                    headers={'Accept': 'application/sparql-results+json'})
                resultBindings = json.loads(response.data.decode("utf-8"))['results']['bindings']

                self.assertEqual(response.status, '200 OK')
                self.assertEqual(len(resultBindings), 1)

                assertResultBindingsEqual(self, resultBindings, [afterPull])

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
            with open(path.join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <urn:graph> .', f.read())

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
            with open(path.join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual('', f.read())

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

            with open(path.join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual(expectedFileContent, f.read())

            # check commit messages
            expectedCommitMsg = 'query: INSERT DATA {graph <urn:graph>'
            expectedCommitMsg += ' {<urn:x> <urn:y> <urn:z> .}}\n\nNew Commit from QuitStore'

            commits = []

            for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
                commits.append(commit.message)

            self.assertEqual(commits, [expectedCommitMsg, 'init'])

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

            with open(path.join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual(expectedFileContent, f.read())

            # check commit messages
            expectedCommitMsg = 'query: INSERT DATA {graph <urn:graph>'
            expectedCommitMsg += ' {<urn:x2> <urn:y2> <urn:z2> .}}\n\nNew Commit from QuitStore'

            commits = []

            for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
                commits.append(commit.message)

            self.assertEqual(commits, [expectedCommitMsg, 'init'])

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

if __name__ == '__main__':
    unittest.main()
