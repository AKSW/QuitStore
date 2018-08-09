from context import quit
import os
from os import path

from datetime import datetime
from pygit2 import GIT_SORT_TOPOLOGICAL, Signature
import quit.application as quitApp
from quit.web.app import create_app
import unittest
from helpers import TemporaryRepository, TemporaryRepositoryFactory
import json
from helpers import createCommit, assertResultBindingsEqual


class SparqlProtocolTests(unittest.TestCase):
    """Test if requests are handled as specified in SPARQL 1.1. Protocol."""

    query = 'SELECT * WHERE {?s ?p ?o}'
    query_base = 'BASE <http://example.org/> SELECT * WHERE {?s ?p <O>}'
    update = 'INSERT {?s ?p ?o} WHERE {?s ?p ?o}'
    update_base = 'BASE <http://example.org/> INSERT {?s ?p ?o} WHERE {?s ?p ?o}'

    def setUp(self):
        return

    def tearDown(self):
        return

    def testQueryViaGet(self):
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            payload = {'query': self.query}
            response = app.get('/sparql', query_string=payload)
            self.assertEqual(response.status_code, 200)

            payload = {'query': self.query, 'default-graph-uri': 'http://example.org/'}
            response = app.get('/sparql', query_string=payload)
            self.assertEqual(response.status_code, 200)

            payload = {'query': self.query, 'named-graph-uri': 'http://example.org/'}
            response = app.get('/sparql', query_string=payload)
            self.assertEqual(response.status_code, 400)

            payload = {'query': self.query,
                       'named-graph-uri': 'http://example.org/1/',
                       'default-graph-uri': 'http://example.org/2/'}
            response = app.get('/sparql', query_string=payload)
            self.assertEqual(response.status_code, 400)

            payload = {'query': self.query_base}
            response = app.get('/sparql', query_string=payload)
            self.assertEqual(response.status_code, 200)

            payload = {'query': self.update}
            response = app.get('/sparql', query_string=payload)
            self.assertEqual(response.status_code, 400)

    def testQueryViaUrlEncodedPost(self):
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            headers = {'Content-Type': 'application/x-www-form-urlencoded'}

            payload = {'query': self.query}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'query': self.query, 'default-graph-uri': 'http://example.org/'}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'query': self.query, 'named-graph-uri': 'http://example.org/'}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 400)

            payload = {'query': self.query,
                       'named-graph-uri': 'http://example.org/1/',
                       'default-graph-uri': 'http://example.org/2/'}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 400)

            payload = {'query': self.query_base}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'query': self.update}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 400)

    def testQueryViaPostDirectly(self):
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            headers = {'Content-Type': 'application/sparql-query'}

            payload = {}
            response = app.post('/sparql', query_string=payload, data=self.query, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'default-graph-uri': 'http://example.org/'}
            response = app.post('/sparql', query_string=payload, data=self.query, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'named-graph-uri': 'http://example.org/'}
            response = app.post('/sparql', query_string=payload, data=self.query, headers=headers)
            self.assertEqual(response.status_code, 400)

            payload = {'default-graph-uri': 'http://example.org/1/',
                       'named-graph-uri': 'http://example.org/2/'}
            response = app.post('/sparql', query_string=payload, data=self.query, headers=headers)
            self.assertEqual(response.status_code, 400)

            payload = {'default-graph-uri': 'http://example.org/1/',
                       'named-graph-uri': 'http://example.org/2/'}
            response = app.post('/sparql', query_string=payload, data=self.query_base, headers=headers)
            self.assertEqual(response.status_code, 400)

            response = app.post('/sparql', data=self.update, headers=headers)
            self.assertEqual(response.status_code, 400)

    def testUpdateViaUrlEncodedPost(self):
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            headers = {'Content-Type': 'application/x-www-form-urlencoded'}

            payload = {'update': self.update}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'update': self.update, 'using-graph-uri': 'http://example.org/'}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'update': self.update, 'using-named-graph-uri': 'http://example.org/'}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 400)

            payload = {'update': self.update,
                       'using-named-graph-uri': 'http://example.org/1/',
                       'using-graph-uri': 'http://example.org/2/'}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 400)

            payload = {'update': self.update_base}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'query': self.update}
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 400)

    def testUpdateViaPostDirectly(self):
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            headers = {'Content-Type': 'application/sparql-update'}

            payload = {}
            response = app.post('/sparql', query_string=payload, data=self.update, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'using-graph-uri': 'http://example.org/'}
            response = app.post('/sparql', query_string=payload, data=self.update, headers=headers)
            self.assertEqual(response.status_code, 200)

            payload = {'using-named-graph-uri': 'http://example.org/'}
            response = app.post('/sparql', query_string=payload, data=self.update, headers=headers)
            self.assertEqual(response.status_code, 400)

            payload = {'using-graph-uri': 'http://example.org/1/',
                       'using-named-graph-uri': 'http://example.org/2/'}
            response = app.post('/sparql', query_string=payload, data=self.update, headers=headers)
            self.assertEqual(response.status_code, 400)

            payload = {'named-graph-uri': 'http://example.org/1/',
                       'using-named-graph-uri': 'http://example.org/2/'}
            response = app.post('/sparql', query_string=payload, data=self.update_base, headers=headers)
            self.assertEqual(response.status_code, 400)

            payload = {'default-graph-uri': 'http://example.org/1/',
                       'named-graph-uri': 'http://example.org/2/'}
            response = app.post('/sparql', query_string=payload, data=self.query, headers=headers)
            self.assertEqual(response.status_code, 400)

    def testUpdateUsingGraphUri(self):
        select = "SELECT * WHERE {graph <urn:graph> {?s ?p ?o .}} ORDER BY ?s ?p ?o"

        # Prepate a git Repository
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/1/> .'
        content2 = '<urn:1> <urn:2> <urn:3> <http://example.org/2/> .'
        repoContent = {'http://example.org/1/': content1,
                       'http://example.org/2/': content2,
                       'urn:graph': ''}

        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select_resp = app.post(
                '/sparql',
                data=dict(query=select),
                headers=dict(accept="application/sparql-results+json")
            )

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 0)

            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            payload = {'update': 'INSERT {GRAPH <urn:graph> {?s ?p ?o}} WHERE {?s ?p ?o}', 'using-graph-uri': 'http://example.org/1/'}

            # execute UPDATE
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 200)

            # execute SELECT query after UPDATE
            select_resp = app.post(
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

    @unittest.skip("Skipped until rdflib properly handles FROM NAMED and USING NAMED")
    def testUpdateUsingNamedGraphUri(self):
        select = "SELECT * WHERE {graph <http://example.org/test/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"

        # Prepate a git Repository
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/graph1/> .'
        content2 = '<urn:1> <urn:2> <urn:3> <http://example.org/graph2/> .'
        repoContent = {'http://example.org/graph1/': content1, 'http://example.org/graph2/': content2, 'http://example.org/test/': ''}

        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select_resp = app.post(
                '/sparql',
                data=dict(query=select),
                headers=dict(accept="application/sparql-results+json")
            )

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 0)

            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            payload = {'update': 'INSERT {GRAPH <http://example.org/test/> {?s ?p ?o}} WHERE {graph ?g {?s ?p ?o}}',
                       'using-named-graph-uri': 'http://example.org/graph1/'}

            # execute UPDATE
            response = app.post('/sparql', data=payload, headers=headers)
            self.assertEqual(response.status_code, 400)

            # execute SELECT query after UPDATE
            select_resp = app.post(
                '/sparql',
                data=dict(query=select),
                headers=dict(accept="application/sparql-results+json")
            )

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            self.assertDictEqual(obj["results"]["bindings"][1], {
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})


class QuitAppTestCase(unittest.TestCase):

    author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
    comitter = Signature('QuitStoreTest', 'quit@quit.aksw.org')

    def setUp(self):
        return

    def tearDown(self):
        return

    def testBaseNamespaceArgument(self):
        """Test if the base namespace is working when changed with by argument.

        1. Prepare a git repository with an empty graph
        2. Start Quit
        3. execute INSERT DATA query
        4. execute SELECT query
        """
        # Prepate a git Repository
        with TemporaryRepositoryFactory().withEmptyGraph("http://example.org/") as repo:

            # Start Quit
            ns = 'http://example.org/newNS/'
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles', '-n', ns])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute INSERT DATA query
            update = "INSERT DATA {graph <http://example.org/> {<relativeURI> <http://ex.org/b> <http://ex.org/c> .}}"
            app.post('/sparql', data=dict(update=update))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://example.org/newNS/relativeURI'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})

    def testBaseNamespaceDefault(self):
        """Test if the base namespace is working.

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
            update = "INSERT DATA {graph <http://example.org/> {<relativeURI> <http://ex.org/b> <http://ex.org/c> .}}"
            app.post('/sparql', data=dict(update=update))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://quit.instance/relativeURI'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})

    def testBaseNamespaceOverwriteInQuery(self):
        """Test if the base namespace is working.

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
            update = "BASE <http://example.org/newNS/>\nINSERT DATA {graph <http://example.org/> "
            update += "{<relativeURI> <http://ex.org/b> <http://ex.org/c> .}}"
            app.post('/sparql', data=dict(update=update))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://example.org/newNS/relativeURI'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})

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

    def testDeleteInsertWhere(self):
        """Test DELETE INSERT WHERE with an empty and a non empty graph.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute DELETE INSERT WHERE query
        5. execute SELECT query
        """
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content, 'http://aksw.org/': ''}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before DELETE INSERT WHERE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute DELETE INSERT WHERE query
            update = 'DELETE {GRAPH <http://example.org/> {?a <urn:y> <urn:z> .}} INSERT {GRAPH <http://aksw.org/> {?a <urn:1> "new" .}} WHERE {GRAPH <http://example.org/> {?a <urn:y> <urn:z> .}}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after DELETE INSERT WHERE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 1)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 1)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:1'},
                "o": {'type': 'literal', 'value': 'new'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:1> "new" <http://aksw.org/> .', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('', f.read())

    @unittest.skip("Skipped until rdflib properly handles FROM NAMED and USING NAMED")
    def testDeleteInsertUsingNamedWhere(self):
        """Test DELETE INSERT WHERE with one graph

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute DELETE INSERT USING NAMED WHERE query
        5. execute SELECT query
        """
        # Prepate a git Repository
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content2 = '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content1, 'http://aksw.org/': content2}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute DELETE INSERT USING NAMED WHERE query
            update = 'DELETE {graph <http://example.org/> {?s1 <urn:y> <urn:z> .} graph <http://aksw.org/> {?s2 <urn:2> <urn:3> .}} '
            update += 'INSERT {graph <http://example.org/> {?s2 <urn:2> ?g2 .} graph <http://aksw.org/> {?s1 <urn:y> ?g1 .}} '
            update += 'USING NAMED <http://example.org/> USING NAMED <http://aksw.org> '
            update += 'WHERE {GRAPH ?g1 {?s1 <urn:y> <urn:z>} . GRAPH ?g2 {?s2 <urn:2> <urn:3> .}}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'http://example.org/'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'http://aksw.org/'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <http://example.org/> <http://aksw.org/> .', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('<urn:1> <urn:2> <http://aksw.org/> <http://example.org/> .', f.read())

    def testDeleteInsertUsingWhere(self):
        """Test DELETE INSERT WHERE with one graph

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute DELETE INSERT USING WHERE query
        5. execute SELECT query
        """
        # Prepate a git Repository
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content2 = '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content1, 'http://aksw.org/': content2}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute DELETE INSERT USING NAMED WHERE query
            update = 'DELETE {graph <http://example.org/> {?s1 <urn:y> <urn:z> .} graph <http://aksw.org/> {?s2 <urn:2> <urn:3> .}} '
            update += 'INSERT {graph <http://example.org/> {?s2 <urn:2> <urn:3> .} graph <http://aksw.org/> {?s1 <urn:y> <urn:z> .}} '
            update += 'USING <http://example.org/> USING <http://aksw.org/> '
            update += 'WHERE {?s1 <urn:y> <urn:z> . ?s2 <urn:2> <urn:3> .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <http://aksw.org/> .', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('<urn:1> <urn:2> <urn:3> <http://example.org/> .', f.read())

    def testDeleteMatchWhere(self):
        """Test DELETE WHERE with two non empty graphs.

        1. Prepare a git repository two non empty graphs
        2. Start Quit
        3. execute SELECT query
        4. execute DELETE match WHERE query
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = '<urn:x> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute DELETE WHERE query
            update = 'DELETE {GRAPH <http://aksw.org/> {?a <urn:2> <urn:3> .}} WHERE {GRAPH <http://example.org/> {?a <urn:y> <urn:z> .}}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 1)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <http://example.org/> .', f.read())

    def testDeleteWhere(self):
        """Test DELETE WHERE with two non empty graphs.

        1. Prepare a git repository two non empty graphs
        2. Start Quit
        3. execute SELECT query
        4. execute DELETE match WHERE query
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = "<urn:x> <urn:2> <urn:3> <http://example.org/> .\n"
        content_example+= "<urn:y> <urn:2> <urn:3> <http://example.org/> .\n"
        repoContent = {'http://example.org/': content_example}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute DELETE WHERE query
            update = 'DELETE WHERE {GRAPH <http://example.org/> {?a <urn:2> <urn:3> .}} '
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:y'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 0)

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('', f.read())

    def testDeleteUsingWhere(self):
        """Test DELETE USING WHERE with two non empty graphs.

        1. Prepare a git repository two non empty graphs
        2. Start Quit
        3. execute SELECT query
        4. execute DELETE USING WHERE query
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = '<urn:x> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute DELETE USING WHERE query
            update = 'DELETE {GRAPH <http://aksw.org/> {?a <urn:2> <urn:3> .}} USING <http://example.org/> WHERE {?a <urn:y> <urn:z> .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 1)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <http://example.org/> .', f.read())

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

    def testInitAndSelectFromNonEmptyGraphPost(self):
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

    def testInitAndSelectFromNonEmptyGraphPostDataInBody(self):
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
                data=select,
                content_type="application/sparql-query",
                headers={"accept": "application/sparql-results+json"}
            )

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            # obj = json.load(select_resp.data)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/x'},
                "p": {'type': 'uri', 'value': 'http://ex.org/y'},
                "o": {'type': 'uri', 'value': 'http://ex.org/z'}})

    def testInitAndSelectFromNonEmptyGraphGet(self):
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

            select_resp = app.get(
                '/sparql',
                query_string=dict(query=select),
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
            app.post('/sparql', data=dict(update=update))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/a'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})

    def testInsertDataAndSelectFromEmptyGraphPostDataInBody(self):
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
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

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
            app.post('/sparql', data=dict(update=update))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 2)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/a'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})

    def testInsertDeleteFromEmptyGraph(self):
        """Test inserting and deleting data and selecting it, starting with an empty graph.

        1. Prepare a git repository with an empty graph
        2. Start Quit
        3. execute INSERT DATA/DELET DATA query
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

            # fill graph with one triple
            insert = "INSERT DATA {graph <http://example.org/> {<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> .}}"
            app.post('/sparql', data=dict(query=insert))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute INSERT and DELETE query
            update = "DELETE DATA {graph <http://example.org/> {<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> .}};"
            update += "INSERT DATA {graph <http://example.org/> {<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> .}}"
            app.post('/sparql', data=dict(update=update))

            # test file content
            expectedFileContent = '<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> <http://example.org/> .'
            with open(path.join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual(expectedFileContent, f.read())

            self.assertFalse(os.path.isfile(path.join(repo.workdir, 'unassigned')))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/a'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})

    def testInsertDeleteFromNonEmptyGraph(self):
        """Test inserting and deleting data and selecting it, starting with a non empty graph.

        1. Prepare a git repository with a non empty graph
        2. Start Quit
        3. execute INSERT DATA/DELET DATA query
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

            # execute INSERT and DELETE query
            update = "DELETE DATA {graph <http://example.org/> {<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> .}};"
            update += "INSERT DATA {graph <http://example.org/> {<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> .}}"
            app.post('/sparql', data=dict(update=update))

            # test file content
            expectedFileContent = '<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> <http://example.org/> .'
            with open(path.join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual(expectedFileContent, f.read())

            self.assertFalse(os.path.isfile(path.join(repo.workdir, 'unassigned')))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            obj = json.loads(select_resp.data.decode("utf-8"))

            self.assertEqual(len(obj["results"]["bindings"]), 1)

            self.assertDictEqual(obj["results"]["bindings"][0], {
                "s": {'type': 'uri', 'value': 'http://ex.org/a'},
                "p": {'type': 'uri', 'value': 'http://ex.org/b'},
                "o": {'type': 'uri', 'value': 'http://ex.org/c'}})

    def testInsertWhere(self):
        """Test INSERT WHERE with an empty and a non empty graph.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute INSERT WHERE query
        5. execute SELECT query
        """
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content, 'http://aksw.org/': ''}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before INSERT WHERE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute INSERT WHERE query
            update = 'INSERT {GRAPH <http://aksw.org/> {?a <urn:1> "new" .}} WHERE {GRAPH <http://example.org/> {?a <urn:y> <urn:z> .}}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after INSERT WHERE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 1)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:1'},
                "o": {'type': 'literal', 'value': 'new'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:1> "new" <http://aksw.org/> .', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <http://example.org/> .', f.read())

    def testInsertWhereVariables(self):
        """Test INSERT WHERE with an empty and a non empty graph.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute INSERT WHERE query
        5. execute SELECT query
        """
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z1> <http://example.org/> .\n'
        content += '<urn:x> <urn:y> <urn:z2> <http://example.org/> .'
        repoContent = {'http://example.org/': content, 'http://aksw.org/': ''}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before INSERT WHERE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute INSERT WHERE query
            update = 'INSERT {GRAPH <http://aksw.org/> {?a <urn:1> "new" .}} WHERE {GRAPH <http://example.org/> {?a <urn:y> ?x .}}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after INSERT WHERE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z1'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z2'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 3)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:1'},
                "o": {'type': 'literal', 'value': 'new'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z1'}})
            self.assertDictEqual(obj["results"]["bindings"][2], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z2'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:1> "new" <http://aksw.org/> .', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual(
                    '<urn:x> <urn:y> <urn:z1> <http://example.org/> .\n<urn:x> <urn:y> <urn:z2> <http://example.org/> .', f.read())

    def testTwoInsertWhereVariables(self):
        """Test two INSERT WHERE (; concatenated) with an empty and a non empty graph.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute INSERT WHERE queries
        5. execute SELECT query
        """
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z1> <http://example.org/> .\n'
        content += '<urn:x> <urn:y> <urn:z2> <http://example.org/> .'
        repoContent = {'http://example.org/': content, 'http://aksw.org/': ''}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before INSERT WHERE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute INSERT WHERE query
            update = 'INSERT {GRAPH <http://aksw.org/> {?a <urn:1> "new" .}} WHERE {GRAPH <http://example.org/> {?a <urn:y> ?x .}}; '
            update += 'INSERT {GRAPH <http://aksw.org/> {?a <urn:1> "new" .}} WHERE {GRAPH <http://example.org/> {?a <urn:y> ?x .}}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after INSERT WHERE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z1'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z2'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 3)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:1'},
                "o": {'type': 'literal', 'value': 'new'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z1'}})
            self.assertDictEqual(obj["results"]["bindings"][2], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z2'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:1> "new" <http://aksw.org/> .', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual(
                    '<urn:x> <urn:y> <urn:z1> <http://example.org/> .\n<urn:x> <urn:y> <urn:z2> <http://example.org/> .', f.read())

    def testInsertUsingWhere(self):
        """Test INSERT USING WHERE with an empty and a non empty graph.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute INSERT WHERE query
        5. execute SELECT query
        """
        # Prepate a git Repository
        content = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content, 'http://aksw.org/': ''}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before INSERT WHERE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute INSERT USING WHERE query
            update = 'INSERT {GRAPH <http://aksw.org/> {?a <urn:1> "new" .}} USING <http://example.org/> WHERE {?a <urn:y> <urn:z> .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after INSERT WHERE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 1)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:1'},
                "o": {'type': 'literal', 'value': 'new'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:1> "new" <http://aksw.org/> .', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <http://example.org/> .', f.read())

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
            app.post('/sparql', data=dict(update=update))

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
            app.post('/sparql', data=dict(update=update))

            # test file content
            expectedFileContent = '<urn:x> <urn:y> <urn:z> <urn:graph> .'

            with open(path.join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual(expectedFileContent, f.read())

            # check commit messages
            expectedCommitMsg = 'query: "INSERT DATA {graph <urn:graph>'
            expectedCommitMsg += ' {<urn:x> <urn:y> <urn:z> .}}"\n\nNew Commit from QuitStore'

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

            update = "INSERT DATA {graph <urn:graph> {<urn:x2> <urn:y2> <urn:z2> .}}"
            app.post('/sparql', data=dict(update=update))

            # test file content
            expectedFileContent = '<urn:x2> <urn:y2> <urn:z2> <urn:graph> .\n'
            expectedFileContent += '<urn:x> <urn:y> <urn:z> <urn:graph> .'

            with open(path.join(repo.workdir, 'graph.nq'), 'r') as f:
                self.assertEqual(expectedFileContent, f.read())

            # check commit messages
            expectedCommitMsg = 'query: "INSERT DATA {graph <urn:graph>'
            expectedCommitMsg += ' {<urn:x2> <urn:y2> <urn:z2> .}}"\n\nNew Commit from QuitStore'

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

    def testWithOnDeleteAndInsert(self):
        """Test WITH on DELETE and INSERT plus USING.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute update
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = '<urn:x> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute UPDATE
            update = 'WITH <http://example.org/> '
            update += 'DELETE {?s1 <urn:y> <urn:z> . GRAPH <http://aksw.org/> {?s1 <urn:2> <urn:3> .}} '
            update += 'INSERT {?s1 <urn:2> <urn:3> . GRAPH <http://aksw.org/> {?s1 <urn:y> <urn:z> .}} '
            update += 'WHERE {?s1 <urn:y> <urn:z> .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <http://aksw.org/> .', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:2> <urn:3> <http://example.org/> .', f.read())

    def testWithOnDeleteAndInsertUsing(self):
        """Test WITH on DELETE and INSERT plus USING.

        1. Prepare a git repository
        2. Start Quit
        3. execute SELECT query
        4. execute update
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute UPDATE
            update = 'WITH <http://aksw.org/> '
            update += 'DELETE {GRAPH <http://example.org/> {?s ?p ?o .} GRAPH <http://aksw.org/> {?s ?p ?o .}} '
            update += 'INSERT {GRAPH <http://aksw.org/> {?s ?p ?o .}} '
            update += 'USING <http://example.org/> '
            update += 'WHERE {?s ?p ?o .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual(
                    '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .\n<urn:x> <urn:y> <urn:z> <http://aksw.org/> .',
                    f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('', f.read())

    @unittest.skip("Skipped until rdflib properly handles FROM NAMED and USING NAMED")
    def testWithOnDeleteAndInsertUsingNamed(self):
        """Test WITH on DELETE and INSERT plus USING NAMED.

        It is expected that USING NAMED will win over WITH and the graph graph IRI can be derived
        from WHERE clause.

        1. Prepare a git repository
        2. Start Quit
        3. execute SELECT query
        4. execute update
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute UPDATE
            update = 'WITH <http://aksw.org/> '
            update += 'DELETE {GRAPH ?g {?s ?p ?o .}} '
            update += 'INSERT {?s ?p ?o .} '
            update += 'USING NAMED <http://example.org/> '
            update += 'WHERE {GRAPH ?g {?s ?p ?o .}}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual(
                    '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .\n<urn:x> <urn:y> <urn:z> <http://aksw.org/> .',
                    f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('', f.read())

    def testWithOnDeleteAndInsert(self):
        """Test WITH on DELETE and INSERT.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute update
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = '<urn:x> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute UPDATE
            update = 'WITH <http://example.org/> '
            update += 'DELETE {?s1 <urn:y> <urn:z> . GRAPH <http://aksw.org/> {?s1 <urn:2> <urn:3> .}} '
            update += 'INSERT {?s1 <urn:2> <urn:3> . GRAPH <http://aksw.org/> {?s1 <urn:y> <urn:z> .}} '
            update += 'WHERE {?s1 <urn:y> <urn:z> .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <http://aksw.org/> .', f.read())
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:2> <urn:3> <http://example.org/> .', f.read())

    def testWithOnDelete(self):
        """Test WITH on DELETE and not on INSERT.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute update
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = ''
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute UPDATE
            update = 'WITH <http://example.org/> '
            update += 'DELETE {?s1 <urn:y> <urn:z> .} '
            update += 'INSERT {?s1 <urn:Y> <urn:Z> . GRAPH <http://aksw.org/> {?s1 <urn:2> <urn:3> .}} '
            update += 'WHERE {?s1 <urn:y> <urn:z> .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 1)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:Y'},
                "o": {'type': 'uri', 'value': 'urn:Z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:2> <urn:3> <http://aksw.org/> .', f.read())
            # compare file content
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:Y> <urn:Z> <http://example.org/> .', f.read())

    def testWithOnDeleteUsing(self):
        """Test WITH on DELETE and not on INSERT plus USING.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute update
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute UPDATE
            update = 'WITH <http://aksw.org/> '
            update += 'DELETE {?s ?p ?o . GRAPH <http://example.org/> {?s ?p ?o .}} '
            update += 'INSERT {?s ?p ?o .} '
            update += 'USING <http://example.org/> '
            update += 'WHERE {?s ?p ?o .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual(
                    '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .\n<urn:x> <urn:y> <urn:z> <http://aksw.org/> .',
                    f.read())
            # compare file content
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('', f.read())

    @unittest.skip("Skipped until rdflib properly handles FROM NAMED and USING NAMED")
    def testWithOnDeleteUsingNamed(self):
        """Test WITH Delete and not on Insert plus USING NAMED.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute update
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute UPDATE
            update = 'WITH <http://aksw.org/> '
            update += 'DELETE {GRAPH ?g {?s ?p ?o .}} '
            update += 'INSERT {?s ?p ?o .} '
            update += 'USING NAMED <http://example.org/> '
            update += 'WHERE {GRAPH ?g {?s ?p ?o .}}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual(
                    '<urn:1> <urn:2> <urn:3> <http://aksw.org/> .\n<urn:x> <urn:y> <urn:z> <http://aksw.org/> .',
                    f.read())
            # compare file content
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('', f.read())

    def testWithOnInsert(self):
        """Test WITH on INSERT and not on DELETE.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute update
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = '<urn:1> <urn:x> <urn:3> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute UPDATE
            update = 'WITH <http://example.org/> '
            update += 'DELETE {GRAPH <http://aksw.org/> {<urn:1> ?s1 <urn:3> .}} '
            update += 'INSERT {?s1 <urn:2> <urn:3> . GRAPH <http://aksw.org/> {?s1 <urn:y> <urn:z> .}} '
            update += 'WHERE {?s1 <urn:y> <urn:z> .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 2)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:1'},
                "p": {'type': 'uri', 'value': 'urn:x'},
                "o": {'type': 'uri', 'value': 'urn:3'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 3)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})
            self.assertDictEqual(obj["results"]["bindings"][2], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})
            self.assertDictEqual(obj["results"]["bindings"][1], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:2'},
                "o": {'type': 'uri', 'value': 'urn:3'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <http://aksw.org/> .', f.read())
            # compare file content
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual(
                    '<urn:x> <urn:2> <urn:3> <http://example.org/> .\n<urn:x> <urn:y> <urn:z> <http://example.org/> .',
                    f.read())

    def testWithOnInsertUsing(self):
        """Test WITH on INSERT and not on DELETE plus USING.

        1. Prepare a git repository with an empty and a non empty graph
        2. Start Quit
        3. execute SELECT query
        4. execute update
        5. execute SELECT query
        """
        # Prepate a git Repository
        content_example = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content_aksw = ''
        repoContent = {'http://example.org/': content_example, 'http://aksw.org/': content_aksw}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo.workdir, '-cm', 'graphfiles'])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute SELECT query before UPDATE
            select = "SELECT * WHERE {graph ?g {?s ?p ?o .}} ORDER BY ?g ?s ?p ?o"
            select_resp_before = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute UPDATE
            update = 'WITH <http://aksw.org/> '
            update += 'DELETE {GRAPH <http://example.org/> {?s ?p ?o .}} '
            update += 'INSERT {?s ?p ?o .} '
            update += 'USING <http://example.org/> '
            update += 'WHERE {?s ?p ?o .}'
            app.post('/sparql',
                     content_type="application/sparql-update",
                     data=update)

            # execute SELECT query after UPDATE
            select_resp_after = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # test select before
            obj = json.loads(select_resp_before.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 1)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://example.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # test select after
            obj = json.loads(select_resp_after.data.decode("utf-8"))
            self.assertEqual(len(obj["results"]["bindings"]), 1)
            self.assertDictEqual(obj["results"]["bindings"][0], {
                "g": {'type': 'uri', 'value': 'http://aksw.org/'},
                "s": {'type': 'uri', 'value': 'urn:x'},
                "p": {'type': 'uri', 'value': 'urn:y'},
                "o": {'type': 'uri', 'value': 'urn:z'}})

            # compare file content
            with open(path.join(repo.workdir, 'graph_0.nq'), 'r') as f:
                self.assertEqual('<urn:x> <urn:y> <urn:z> <http://aksw.org/> .', f.read())
            # compare file content
            with open(path.join(repo.workdir, 'graph_1.nq'), 'r') as f:
                self.assertEqual('', f.read())


if __name__ == '__main__':
    unittest.main()
