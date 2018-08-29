#!/usr/bin/env python3

import unittest
from context import quit
from itertools import chain
from quit.helpers import configure_query_dataset, configure_update_dataset
from quit.helpers import parse_query_type, parse_update_type
from quit.exceptions import SparqlProtocolError, NonAbsoluteBaseError, UnSupportedQuery
from rdflib import URIRef
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate


class BaseNamespaceTests(unittest.TestCase):
    """Test Base Namespaces in querystring and as argument."""

    def testBaseNamespace(self):
        select = "PREFIX ex: <http://ex.org/> BASE <http://good.example/> SELECT * WHERE { ?s ?p ?o }"
        update = "PREFIX ex: <http://ex.org/> BASE <http://good.example/> INSERT DATA { <1> <2> <3> }"
        construct = "PREFIX ex: <http://ex.org/> BASE <http://good.example/> CONSTRUCT { ?s <2> <3> } WHERE { ?s ?p ?o }"

        queryType, parsedQuery = parse_query_type(select)
        self.assertEqual(queryType, 'SelectQuery')

        queryType, parsedQuery = parse_update_type(update)
        self.assertEqual(parsedQuery[0]['triples'][0][0], URIRef('http://good.example/1'))
        self.assertEqual(parsedQuery[0]['triples'][0][1], URIRef('http://good.example/2'))
        self.assertEqual(parsedQuery[0]['triples'][0][2], URIRef('http://good.example/3'))
        self.assertEqual(queryType, 'InsertData')

        queryType, parsedQuery = parse_query_type(construct)
        self.assertEqual(queryType, 'ConstructQuery')

    def testBadBaseNamespace(self):
        select = "PREFIX ex: <http://ex.org/> BASE <bad.example/> SELECT * WHERE { ?s ?p ?o }"
        update = "PREFIX ex: <http://ex.org/> BASE <bad.example/> INSERT DATA { <1> <2> <3> }"
        construct = "PREFIX ex: <http://ex.org/> BASE <bad.example/> CONSTRUCT { ?s <2> <3> } WHERE { ?s ?p ?o }"

        self.assertRaises(NonAbsoluteBaseError, parse_query_type, select)
        self.assertRaises(NonAbsoluteBaseError, parse_update_type, update)
        self.assertRaises(NonAbsoluteBaseError, parse_query_type, construct)

    def testOverwrittenBaseNamespace(self):
        update1 = "PREFIX ex: <http://ex.org/> INSERT DATA { <1> <2> <3> }"
        update2 = "PREFIX ex: <http://ex.org/> BASE <http://in-query/> INSERT DATA { <1> <2> <3> }"

        queryType, parsedQuery = parse_update_type(update1, 'http://argument/')
        self.assertEqual(parsedQuery[0]['triples'][0][0], URIRef('http://argument/1'))
        self.assertEqual(parsedQuery[0]['triples'][0][1], URIRef('http://argument/2'))
        self.assertEqual(parsedQuery[0]['triples'][0][2], URIRef('http://argument/3'))
        self.assertEqual(queryType, 'InsertData')

        queryType, parsedQuery = parse_update_type(update2, 'http://argument/')
        self.assertEqual(parsedQuery[0]['triples'][0][0], URIRef('http://in-query/1'))
        self.assertEqual(parsedQuery[0]['triples'][0][1], URIRef('http://in-query/2'))
        self.assertEqual(parsedQuery[0]['triples'][0][2], URIRef('http://in-query/3'))
        self.assertEqual(queryType, 'InsertData')

    def testOverwrittenBadBaseNamespace(self):
        update = "PREFIX ex: <http://ex.org/> BASE <bad.base> INSERT DATA { <1> <2> <3> }"

        self.assertRaises(NonAbsoluteBaseError, parse_update_type, update, 'http://argument/')


class QueryTypeTests(unittest.TestCase):

    def testQueryTypes(self):
        """Test allowed queries."""
        id_pattern = """ {GRAPH <urn:graph1> { ?s ?p ?o }} WHERE {GRAPH <urn:graph2> { ?s ?p ?o}}"""

        queries = {
            "SELECT * WHERE {graph ?g {?s ?p ?o .}}": 'SelectQuery',
            "DESCRIBE ?s WHERE {graph ?g {?s <urn:1> <urn:2> .}}": 'DescribeQuery',
            "CONSTRUCT {?s ?p ?o} WHERE {graph ?g {?s ?p ?o .}}": 'ConstructQuery',
            'ASK  { ?x <urn:name>  "Alice" }': 'AskQuery',
        }

        prefix_queries = {
            'PREFIX ask: <http://creator/load>\n'
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

        prefix_updates = {
            "PREFIX ask: <http://creator/load> INSERT DATA { <1> <2> <3> }": 'InsertData',
            "PREFIX ask: <http://creator/load> DELETE DATA { <1> <2> <3> } ;"
            "INSERT DATA { <1> <2> <3> } ": 'DeleteData'
        }

        unsupported_queries = {
            "foo bar": "unsupported",
            "SELECT * WHERE { s p o }": "unsupported",
            "INSERT DATA { s p o }": "unsupported",
        }

        all_queries = chain(
            queries.items(),
            prefix_queries.items(),
        )

        all_updates = chain(
            updates.items(),
            prefix_updates.items(),
        )

        for query, expected in all_queries:
            querytype, parsedquery = parse_query_type(query)
            self.assertEqual(querytype, expected, query)

        for update, expected in all_updates:
            queryType, parsedQuery = parse_update_type(update)
            self.assertEqual(queryType, expected, update)

        for query, expected in unsupported_queries.items():
            self.assertRaises(UnSupportedQuery, parse_query_type, query)

        for query, expected in unsupported_queries.items():
            self.assertRaises(UnSupportedQuery, parse_update_type, query)

    def testQueryTypesWithNamedGraph(self):
        """Test allowed queries with named graph from SPARQL Request."""
        id_pattern = """ {GRAPH <urn:graph1> { ?s ?p ?o }} WHERE {GRAPH <urn:graph2> { ?s ?p ?o}}"""

        queries = {
            "SELECT * WHERE {graph ?g {?s ?p ?o .}}": 'SelectQuery',
            "DESCRIBE ?s WHERE {graph ?g {?s <urn:1> <urn:2> .}}": 'DescribeQuery',
            "CONSTRUCT {?s ?p ?o} WHERE {graph ?g {?s ?p ?o .}}": 'ConstructQuery',
            'ASK  { ?x <urn:name>  "Alice" }': 'AskQuery',
        }

        prefix_queries = {
            "PREFIX ask: <http://creator/load>\n"
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

        prefix_updates = {
            "PREFIX ask: <http://creator/load> INSERT DATA { <1> <2> <3> }": 'InsertData',
            "PREFIX ask: <http://creator/load> DELETE DATA { <1> <2> <3> } ;"
            "INSERT DATA { <1> <2> <3> } ": 'DeleteData'
        }

        all_queries = chain(
            queries.items(),
            prefix_queries.items(),
        )

        all_updates = chain(
            updates.items(),
            prefix_updates.items(),
        )

        for query, expected in all_queries:
            queryType, parsedQuery = parse_query_type(query, None, [], ['http://to.inject/'])
            self.assertEqual(queryType, expected, query)

        for update, expected in all_updates:
            queryType, parsedQuery = parse_update_type(update, None, ['http://to.inject/'], [])
            self.assertEqual(queryType, expected, update)


class QueryRewritingTests(unittest.TestCase):
    """Test datasets will be selected according to SPARQL 1.1. Protocol for queries and updates."""

    query = 'SELECT * WHERE {?s ?p ?o}'
    query_from = ' SELECT * FROM <http://example.org/default/> WHERE {?s ?p ?o}'
    query_named = ' SELECT * FROM NAMED <http://example.org/named/> WHERE {?s ?p ?o}'
    query_both = ' SELECT * FROM <http://example.org/default/> '
    query_both += 'FROM NAMED <http://example.org/named/> WHERE {?s ?p ?o}'

    update = 'INSERT {?s ?p ?o} WHERE {?s ?p ?o}'
    update_with = 'WITH <http://example.org/with/> INSERT {?s ?p ?o} WHERE {?s ?p ?o}'
    update_using = 'INSERT {?s ?p ?o} USING <http://example.org/default/> WHERE {?s ?p ?o}'
    update_named = 'INSERT {?s ?p ?o} USING NAMED <http://example.org/named/> WHERE {?s ?p ?o}'
    update_both = 'INSERT {?s ?p ?o} USING NAMED <http://example.org/named/> '
    update_both += 'USING <http://example.org/default/> WHERE {?s ?p ?o}'

    def testSelect(self):
        parsed_query = configure_query_dataset(parseQuery(self.query), [], [])
        self.assertEqual(len(parsed_query[1]), 1)
        self.assertTrue('where' in parsed_query[1])

        parsed_query = configure_query_dataset(parseQuery(self.query), None, None)
        self.assertEqual(len(parsed_query[1]), 1)
        self.assertTrue('where' in parsed_query[1])

        parsed_query = configure_query_dataset(parseQuery(self.query), [], None)
        self.assertEqual(len(parsed_query[1]), 1)
        self.assertTrue('where' in parsed_query[1])

        parsed_query = configure_query_dataset(parseQuery(self.query), None, [])
        self.assertEqual(len(parsed_query[1]), 1)
        self.assertTrue('where' in parsed_query[1])

        parsed_query = configure_query_dataset(parseQuery(self.query), ['urn:default'], [])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))

        parsed_query = configure_query_dataset(parseQuery(self.query), [], ['urn:named'])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['named'], URIRef('urn:named'))

        parsed_query = configure_query_dataset(parseQuery(self.query), ['urn:default'], ['urn:named'])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query[1]['datasetClause'][1]['named'], URIRef('urn:named'))

    def testSelectFrom(self):
        parsed_query = configure_query_dataset(parseQuery(self.query_from), [], [])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(
            parsed_query[1]['datasetClause'][0]['default'], URIRef('http://example.org/default/'))

        parsed_query = configure_query_dataset(parseQuery(self.query_from), ['urn:default'], [])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))

        parsed_query = configure_query_dataset(parseQuery(self.query_from), [], ['urn:named'])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['named'], URIRef('urn:named'))

        parsed_query = configure_query_dataset(parseQuery(self.query_from), ['urn:default'], ['urn:named'])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query[1]['datasetClause'][1]['named'], URIRef('urn:named'))

    def testSelectFromNamed(self):
        parsed_query = configure_query_dataset(parseQuery(self.query_named), [], [])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(
            parsed_query[1]['datasetClause'][0]['named'], URIRef('http://example.org/named/'))

        parsed_query = configure_query_dataset(parseQuery(self.query_named), ['urn:default'], [])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))

        parsed_query = configure_query_dataset(parseQuery(self.query_from), [], ['urn:named'])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['named'], URIRef('urn:named'))

        parsed_query = configure_query_dataset(parseQuery(self.query_from), ['urn:default'], ['urn:named'])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query[1]['datasetClause'][1]['named'], URIRef('urn:named'))

    def testSelectFromAndFromNamed(self):
        parsed_query = configure_query_dataset(parseQuery(self.query_both), [], [])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(
            parsed_query[1]['datasetClause'][0]['default'], URIRef('http://example.org/default/'))
        self.assertEqual(
            parsed_query[1]['datasetClause'][1]['named'], URIRef('http://example.org/named/'))

        parsed_query = configure_query_dataset(parseQuery(self.query_both), ['urn:default'], [])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))

        parsed_query = configure_query_dataset(parseQuery(self.query_both), [], ['urn:named'])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['named'], URIRef('urn:named'))

        parsed_query = configure_query_dataset(parseQuery(self.query_both), ['urn:default'], ['urn:named'])
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query[1]['datasetClause'][1]['named'], URIRef('urn:named'))

    def testUpdate(self):
        parsed_query = configure_update_dataset(parseUpdate(self.update), [], [])
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 2)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])

        parsed_query = configure_update_dataset(parseUpdate(self.update), None, None)
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 2)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])

        parsed_query = configure_update_dataset(parseUpdate(self.update), [], None)
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 2)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])

        parsed_query = configure_update_dataset(parseUpdate(self.update), None, [])
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 2)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])

        parsed_query = configure_update_dataset(parseUpdate(self.update), ['urn:default'], [])
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertTrue('using' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 1)
        self.assertEqual(parsed_query.request[0]['using'][0]['default'], URIRef('urn:default'))

        parsed_query = configure_update_dataset(parseUpdate(self.update), [], ['urn:named'])
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertTrue('using' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 1)
        self.assertEqual(parsed_query.request[0]['using'][0]['named'], URIRef('urn:named'))

        parsed_query = configure_update_dataset(parseUpdate(self.update), ['urn:default'], ['urn:named'])
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertTrue('using' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 2)
        self.assertEqual(parsed_query.request[0]['using'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query.request[0]['using'][1]['named'], URIRef('urn:named'))

    def testUpdateWith(self):
        parsed_query = configure_update_dataset(parseUpdate(self.update_with), [], [])
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('withClause' in parsed_query.request[0])
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertEqual(parsed_query.request[0]['withClause'], URIRef('http://example.org/with/'))

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_with), [], ['urn:named'])

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_with), ['urn:default'], [])

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_with), ['urn:default'], ['urn:named'])

    def testUpdateUsing(self):
        parsed_query = configure_update_dataset(parseUpdate(self.update_using), [], [])
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('using' in parsed_query.request[0])
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 1)
        self.assertEqual(
            parsed_query.request[0]['using'][0]['default'], URIRef('http://example.org/default/'))

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_using), [], ['urn:named'])

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_using), ['urn:default'], [])

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_using), ['urn:default'], ['urn:named'])

    def testUpdateUsingNamed(self):
        parsed_query = configure_update_dataset(parseUpdate(self.update_named), [], [])
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('using' in parsed_query.request[0])
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 1)
        self.assertEqual(
            parsed_query.request[0]['using'][0]['named'], URIRef('http://example.org/named/'))

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_named), [], ['urn:named'])

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_named), ['urn:default'], [])

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_named), ['urn:default'], ['urn:named'])

    def testUpdateUsingAndUsingNamed(self):
        parsed_query = configure_update_dataset(parseUpdate(self.update_both), [], [])
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('using' in parsed_query.request[0])
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 2)
        self.assertEqual(
            parsed_query.request[0]['using'][0]['named'], URIRef('http://example.org/named/'))
        self.assertEqual(
            parsed_query.request[0]['using'][1]['default'], URIRef('http://example.org/default/'))

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_named), [], ['urn:named'])

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_named), ['urn:default'], [])

        self.assertRaises(SparqlProtocolError,
                          configure_update_dataset, parseUpdate(self.update_named), ['urn:default'], ['urn:named'])


def main():
    unittest.main()


if __name__ == '__main__':
    main()
