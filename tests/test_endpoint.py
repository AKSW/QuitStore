#!/usr/bin/env python3
import unittest
from context import quit

import quit.application as quitApp
from quit.web.app import create_app
from tempfile import TemporaryDirectory
import json

class EndpointTests(unittest.TestCase):
    """Test endpoint features."""

    def setUp(self):
        return

    def tearDown(self):
        return

    def testInsertDataNoSnapshotIsolation(self):
        """Test inserting data and selecting it, starting with an empty directory.

        1. Prepare an empty directory
        2. Start Quit
        3. execute INSERT DATA query
        4. execute SELECT query
        """
        # Prepate a git Repository
        with TemporaryDirectory() as repo:

            # Start Quit
            args = quitApp.parseArgs(['-t', repo])
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()

            # execute INSERT DATA query
            update = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> a <http://ex.org/Todo> ;
                  <http://ex.org/task> "Take out the organic waste" .
            }}
            """
            app.post('/sparql', data=dict(update=update))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

            # execute INSERT DATA query
            update = """INSERT DATA {
            GRAPH <http://example.org/> {
                <http://ex.org/garbage> <http://ex.org/status> <http://ex.org/completed> .
            }}
            """
            app.post('/sparql', data=dict(update=update))

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
            app.post('/sparql', data=dict(update=update))

            # execute SELECT query
            select = "SELECT * WHERE {graph <http://example.org/> {?s a <http://ex.org/Todo> ; ?p ?o .}} ORDER BY ?s ?p ?o"
            select_resp = app.post('/sparql', data=dict(query=select), headers=dict(accept="application/sparql-results+json"))

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


if __name__ == '__main__':
    unittest.main()
