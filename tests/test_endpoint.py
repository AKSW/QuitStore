#!/usr/bin/env python3
import unittest
from context import quit
from glob import glob
from os import remove
from os.path import join, isdir
from quit.web.modules import endpoint
from quit.exceptions import UnSupportedQueryType
from rdflib.term import URIRef
from itertools import chain


class QuitEndpointTestCase(unittest.TestCase):

    def testQueryTypes(self):
        """
        Test allowed queries.

        The endpoint uses a regex to classify all SPARQL queries. After this it will be distinguish
        between CONSTRUCT/DESCRIBE, SELECT/ASK and rest. The last case results in an update
        execution.
        """
        ep = endpoint
        id_pattern = """ {GRAPH <urn:graph1> { ?s ?p ?o }} WHERE {GRAPH <urn:graph2> { ?s ?p ?o}}"""

        queries = {
            "SELECT * WHERE {graph ?g {?s ?p ?o .}}": 'SelectQuery',
            "DESCRIBE ?s WHERE {graph ?g {?s <urn:1> <urn:2> .}}": 'DescribeQuery',
            "CONSTRUCT {?s ?p ?o} WHERE {graph ?g {?s ?p ?o .}}": 'ConstructQuery',
            'ASK  { ?x <urn:name>  "Alice" }': 'AskQuery',
        }

        updates = {
            "INSERT DATA { <1> <2> <3> }": 'InsertData',
            "DELETE DATA { <1> <2> <3> }": 'DeleteData',
            "INSERT " + id_pattern: 'Modify',
            "DELETE " + id_pattern: 'Modify',
            "INSERT " + id_pattern + '; DELETE' + id_pattern: 'Modify',
            "CLEAR  GRAPH <urn:graph1>": 'Clear',
            "CREATE  GRAPH <urn:graph1>": 'Create',
            "DROP  GRAPH <urn:graph1>": 'Drop',
            "COPY  <urn:graph1> TO <urn:graph2>": 'Copy',
            "MOVE  <urn:graph1> TO <urn:graph2>": 'Move',
            "ADD  <urn:graph1> TO <urn:graph2>": 'Add',
        }

        prefix_queries = {
            "PREFIX ask: <http://creator/load> INSERT DATA { <1> <2> <3> }": 'InsertData',
            "PREFIX ask: <http://creator/load>\n"
            'ASK  { ?x <urn:name>  "Alice" }': 'AskQuery',
            "PREFIX ask: <http://creator/load> DELETE DATA { <1> <2> <3> } ;"
            "INSERT DATA { <1> <2> <3> } ": 'DeleteData'
        }

        unsupported_queries = {
            "foo bar": "unsupported",
            "LOAD  <urn:graph1> INTO <urn:graph2>": 'Load'
        }

        all_queries = chain(
            queries.items(),
            updates.items(),
            prefix_queries.items(),
        )

        for query, expected in all_queries:
            queryType, parsedQuery = ep.parse_query_type(query)
            self.assertEqual(queryType, expected, query)

        for query, expected in unsupported_queries.items():
            with self.assertRaises(UnSupportedQueryType):
                ep.parse_query_type(query)

    def testBaseNamespace(self):
        ep = endpoint
        update = "INSERT DATA { <1> <2> <3> }"

        queryType, parsedQuery = ep.parse_query_type(update, 'http://good.example/')
        self.assertEqual(parsedQuery[0]['triples'][0][0], URIRef('http://good.example/1'))
        self.assertEqual(parsedQuery[0]['triples'][0][1], URIRef('http://good.example/2'))
        self.assertEqual(parsedQuery[0]['triples'][0][2], URIRef('http://good.example/3'))
        self.assertEqual(queryType, 'InsertData')

    def testNoneBaseNamespace(self):
        ep = endpoint
        update = "INSERT DATA { <1> <2> <3> }"

        queryType, parsedQuery = ep.parse_query_type(update)
        self.assertEqual(parsedQuery[0]['triples'][0][0], URIRef('1'))
        self.assertEqual(parsedQuery[0]['triples'][0][1], URIRef('2'))
        self.assertEqual(parsedQuery[0]['triples'][0][2], URIRef('3'))
        self.assertEqual(queryType, 'InsertData')

    def testOverwrittenBaseNamespace(self):
        ep = endpoint
        update = "BASE <http://better.example/> INSERT DATA { <1> <2> <3> }"

        queryType, parsedQuery = ep.parse_query_type(update, 'http://good.example/')
        self.assertEqual(parsedQuery[0]['triples'][0][0], URIRef('http://better.example/1'))
        self.assertEqual(parsedQuery[0]['triples'][0][1], URIRef('http://better.example/2'))
        self.assertEqual(parsedQuery[0]['triples'][0][2], URIRef('http://better.example/3'))
        self.assertEqual(queryType, 'InsertData')


if __name__ == '__main__':
    unittest.main()
