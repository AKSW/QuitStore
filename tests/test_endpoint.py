#!/usr/bin/env python3
import unittest
from context import quit
from glob import glob
from os import remove
from os.path import join, isdir
from quit.web.modules import endpoint
from quit.exceptions import UnSupportedQueryType

class QuitEndpointTestCase(unittest.TestCase):

    def testQueryTypes(self):
        """
        Test allowed queries.

        The endpoint uses a regex to classify all SPARQL queries. After this it will be distinguish
        between CONSTRUCT/DESCRIBE, SELECT/ASK and rest. The last case results in an update
        execution.
        """
        ep = endpoint
        id_pattern = """ {GRAPH <urn:graph1> { ?s ?p ?o }} WHERE {GRAPH <urn:graph2{ ?s ?p ?o}}"""

        queries = {
            "SELECT * WHERE {graph ?g {?s ?p ?o .}}": 'SELECT',
            "CONSTRUCT {?s ?p ?o} WHERE {graph ?g {?s ?p ?o .}}": 'CONSTRUCT',
            'ASK  { ?x foaf:name  "Alice" }': 'ASK',
            "INSERT DATA { <1> <2> <3> }": 'INSERT',
            "DELETE DATA { <1> <2> <3> }": 'DELETE',
            "INSERT " + id_pattern: 'INSERT',
            "DELETE " + id_pattern: 'DELETE',
            "INSERT " + id_pattern + '; DELETE' + id_pattern: 'INSERT',
            "CLEAR  GRAPH <urn:graph1>": 'CLEAR',
            "CREATE  GRAPH <urn:graph1>": 'CREATE',
            "DROP  GRAPH <urn:graph1>": 'DROP',
            "COPY  <urn:graph1> TO <urn:graph2>": 'COPY',
            "MOVE  <urn:graph1> TO <urn:graph2>": 'MOVE',
            "ADD  <urn:graph1> TO <urn:graph2>": 'ADD',
            "LOAD  <urn:graph1> INTO <urn:graph2>": 'LOAD'
        }

        for query, expected in queries.items():
            query_type = ep.parse_query_type(query)
            self.assertEqual(query_type, expected)

        with self.assertRaises(UnSupportedQueryType) as context:
            ep.parse_query_type('foo bar')

if __name__ == '__main__':
    unittest.main()
