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
        select = "PREFIX ex: <http://ex.org/> BASE <http://good.example/> SELECT * WHERE { ?s ?p ?o }"
        update = "PREFIX ex: <http://ex.org/> BASE <http://good.example/> INSERT DATA { <1> <2> <3> }"
        construct = "PREFIX ex: <http://ex.org/> BASE <http://good.example/> CONSTRUCT { ?s <2> <3> } WHERE { ?s ?p ?o }"

        queryType, parsedQuery = ep.parse_query_type(select)
        self.assertEqual(queryType, 'SelectQuery')

        queryType, parsedQuery = ep.parse_query_type(update)
        self.assertEqual(parsedQuery[0]['triples'][0][0], URIRef('http://good.example/1'))
        self.assertEqual(parsedQuery[0]['triples'][0][1], URIRef('http://good.example/2'))
        self.assertEqual(parsedQuery[0]['triples'][0][2], URIRef('http://good.example/3'))
        self.assertEqual(queryType, 'InsertData')

        queryType, parsedQuery = ep.parse_query_type(construct)
        self.assertEqual(queryType, 'ConstructQuery')

    def testBadBaseNamespace(self):
        ep = endpoint
        select = "PREFIX ex: <http://ex.org/> BASE <bad.example/> SELECT * WHERE { ?s ?p ?o }"
        update = "PREFIX ex: <http://ex.org/> BASE <bad.example/> INSERT DATA { <1> <2> <3> }"
        construct = "PREFIX ex: <http://ex.org/> BASE <bad.example/> CONSTRUCT { ?s <2> <3> } WHERE { ?s ?p ?o }"

        self.assertRaises(UnSupportedQueryType, ep.parse_query_type, select)
        self.assertRaises(UnSupportedQueryType, ep.parse_query_type, update)
        self.assertRaises(UnSupportedQueryType, ep.parse_query_type, construct)

    def testOverwrittenBaseNamespace(self):
        ep = endpoint
        update1 = "PREFIX ex: <http://ex.org/> INSERT DATA { <1> <2> <3> }"
        update2 = "PREFIX ex: <http://ex.org/> BASE <http://in-query//> INSERT DATA { <1> <2> <3> }"

        queryType, parsedQuery = ep.parse_query_type(update1, 'http://argument/')
        self.assertEqual(parsedQuery[0]['triples'][0][0], URIRef('http://argument/1'))
        self.assertEqual(parsedQuery[0]['triples'][0][1], URIRef('http://argument/2'))
        self.assertEqual(parsedQuery[0]['triples'][0][2], URIRef('http://argument/3'))
        self.assertEqual(queryType, 'InsertData')

        queryType, parsedQuery = ep.parse_query_type(update2, 'http://argument/')
        self.assertEqual(parsedQuery[0]['triples'][0][0], URIRef('http://in-query/1'))
        self.assertEqual(parsedQuery[0]['triples'][0][1], URIRef('http://in-query/2'))
        self.assertEqual(parsedQuery[0]['triples'][0][2], URIRef('http://in-query/3'))
        self.assertEqual(queryType, 'InsertData')

    def testOverwrittenBadBaseNamespace(self):
        ep = endpoint
        update = "PREFIX ex: <http://ex.org/> BASE <bad.base> INSERT DATA { <1> <2> <3> }"

        self.assertRaises(UnSupportedQueryType, ep.parse_query_type, update, 'http://argument/')

if __name__ == '__main__':
    unittest.main()
