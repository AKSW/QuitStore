#!/usr/bin/env python3

import unittest
from context import quit
from rdflib import URIRef
from quit.helpers import rewrite_graphs
from quit.exceptions import SparqlProtocolError
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate


class QueryRewritingTests(unittest.TestCase):
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

    def testSimpleSelectQuery(self):
        parsed_query = rewrite_graphs(parseQuery(self.query), [], [], 'query')
        self.assertEqual(len(parsed_query[1]), 1)
        self.assertTrue('where' in parsed_query[1])

        parsed_query = rewrite_graphs(parseQuery(self.query), ['urn:default'], [], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))

        parsed_query = rewrite_graphs(parseQuery(self.query), [], ['urn:named'], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['named'], URIRef('urn:named'))

        parsed_query = rewrite_graphs(parseQuery(self.query), ['urn:default'], ['urn:named'], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query[1]['datasetClause'][1]['named'], URIRef('urn:named'))

    def testSelectFrom(self):
        parsed_query = rewrite_graphs(parseQuery(self.query_from), [], [], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(
            parsed_query[1]['datasetClause'][0]['default'], URIRef('http://example.org/default/'))

        parsed_query = rewrite_graphs(parseQuery(self.query_from), ['urn:default'], [], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))

        parsed_query = rewrite_graphs(parseQuery(self.query_from), [], ['urn:named'], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['named'], URIRef('urn:named'))

        parsed_query = rewrite_graphs(parseQuery(self.query_from), ['urn:default'], ['urn:named'], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query[1]['datasetClause'][1]['named'], URIRef('urn:named'))

    def testSelectFromNamed(self):
        parsed_query = rewrite_graphs(parseQuery(self.query_named), [], [], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(
            parsed_query[1]['datasetClause'][0]['named'], URIRef('http://example.org/named/'))

        parsed_query = rewrite_graphs(parseQuery(self.query_named), ['urn:default'], [], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))

        parsed_query = rewrite_graphs(parseQuery(self.query_from), [], ['urn:named'], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['named'], URIRef('urn:named'))

        parsed_query = rewrite_graphs(parseQuery(self.query_from), ['urn:default'], ['urn:named'], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query[1]['datasetClause'][1]['named'], URIRef('urn:named'))

    def testSelectFromAndFromNamed(self):
        parsed_query = rewrite_graphs(parseQuery(self.query_both), [], [], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(
            parsed_query[1]['datasetClause'][0]['default'], URIRef('http://example.org/default/'))
        self.assertEqual(
            parsed_query[1]['datasetClause'][1]['named'], URIRef('http://example.org/named/'))

        parsed_query = rewrite_graphs(parseQuery(self.query_both), ['urn:default'], [], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))

        parsed_query = rewrite_graphs(parseQuery(self.query_both), [], ['urn:named'], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 1)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['named'], URIRef('urn:named'))

        parsed_query = rewrite_graphs(parseQuery(self.query_both), ['urn:default'], ['urn:named'], 'query')
        self.assertEqual(len(parsed_query[1]), 2)
        self.assertTrue('where' in parsed_query[1])
        self.assertTrue('datasetClause' in parsed_query[1])
        self.assertEqual(len(parsed_query[1]['datasetClause']), 2)
        self.assertEqual(parsed_query[1]['datasetClause'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query[1]['datasetClause'][1]['named'], URIRef('urn:named'))

    def testUpdate(self):
        parsed_query = rewrite_graphs(parseUpdate(self.update), [], [], 'update')
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 2)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])

        parsed_query = rewrite_graphs(parseUpdate(self.update), ['urn:default'], [], 'update')
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertTrue('using' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 1)
        self.assertEqual(parsed_query.request[0]['using'][0]['default'], URIRef('urn:default'))

        parsed_query = rewrite_graphs(parseUpdate(self.update), [], ['urn:named'], 'update')
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertTrue('using' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 1)
        self.assertEqual(parsed_query.request[0]['using'][0]['named'], URIRef('urn:named'))

        parsed_query = rewrite_graphs(parseUpdate(self.update), ['urn:default'], ['urn:named'], 'update')
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertTrue('using' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 2)
        self.assertEqual(parsed_query.request[0]['using'][0]['default'], URIRef('urn:default'))
        self.assertEqual(parsed_query.request[0]['using'][1]['named'], URIRef('urn:named'))

    def testUpdateWith(self):
        parsed_query = rewrite_graphs(parseUpdate(self.update_with), [], [], 'update')
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('withClause' in parsed_query.request[0])
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertEqual(parsed_query.request[0]['withClause'], URIRef('http://example.org/with/'))

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_with), [], ['urn:named'], 'update')

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_with), ['urn:default'], [], 'update')

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_with), ['urn:default'], ['urn:named'], 'update')

    def testUpdateUsing(self):
        parsed_query = rewrite_graphs(parseUpdate(self.update_using), [], [], 'update')
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('using' in parsed_query.request[0])
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 1)
        self.assertEqual(
            parsed_query.request[0]['using'][0]['default'], URIRef('http://example.org/default/'))

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_using), [], ['urn:named'], 'update')

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_using), ['urn:default'], [], 'update')

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_using), ['urn:default'], ['urn:named'], 'update')

    def testUpdateUsingNamed(self):
        parsed_query = rewrite_graphs(parseUpdate(self.update_named), [], [], 'update')
        self.assertEqual(len(parsed_query.request), 1)
        self.assertEqual(len(parsed_query.request[0]), 3)
        self.assertTrue('using' in parsed_query.request[0])
        self.assertTrue('insert' in parsed_query.request[0])
        self.assertTrue('where' in parsed_query.request[0])
        self.assertEqual(len(parsed_query.request[0]['using']), 1)
        self.assertEqual(
            parsed_query.request[0]['using'][0]['named'], URIRef('http://example.org/named/'))

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_named), [], ['urn:named'], 'update')

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_named), ['urn:default'], [], 'update')

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_named), ['urn:default'], ['urn:named'], 'update')

    def testUpdateUsingAndUsingNamed(self):
        parsed_query = rewrite_graphs(parseUpdate(self.update_both), [], [], 'update')
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
                          rewrite_graphs, parseUpdate(self.update_named), [], ['urn:named'], 'update')

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_named), ['urn:default'], [], 'update')

        self.assertRaises(SparqlProtocolError,
                          rewrite_graphs, parseUpdate(self.update_named), ['urn:default'], ['urn:named'], 'update')


def main():
    unittest.main()


if __name__ == '__main__':
    main()
