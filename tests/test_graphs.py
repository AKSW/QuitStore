#!/usr/bin/env python3

import unittest
from context import quit
from quit.graphs import RewriteGraph, CopyOnEditGraph
from quit.graphs import InMemoryAggregatedGraph, InMemoryCopyOnEditAggregatedGraph
from os import path, environ
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from rdflib import Graph, URIRef
from tempfile import TemporaryDirectory, NamedTemporaryFile


class RewriteGraphTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


class CopyOnEditGraphTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


class InMemoryAggregatedGraphTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testInitEmptyGraph(self):
        iGraph = InMemoryAggregatedGraph()
        contexts = iGraph.contexts()
        self.assertEqual(len(contexts), 0)
        self.assertEqual(len(iGraph), 0)

    def testInitEmptyGraphWithContext(self):
        iGraph = InMemoryAggregatedGraph(graphs=[Graph(identifier='urn:graph')])
        contexts = iGraph.contexts()
        self.assertEqual(len(contexts), 1)
        self.assertEqual(len(iGraph), 0)

    def testInitNonEmptyGraph(self):
        g = Graph(identifier='urn:graph')
        g.add((URIRef('urn:1'), URIRef('urn:2'), URIRef('urn:3')))

        iGraph = InMemoryAggregatedGraph(graphs=[g])
        contexts = iGraph.contexts()
        self.assertEqual(len(contexts), 1)
        self.assertEqual(len(iGraph), 1)

    def testGetExistingContext(self):
        g = Graph(identifier='urn:graph')
        g.add((URIRef('urn:1'), URIRef('urn:2'), URIRef('urn:3')))
        self.assertEqual(len(g), 1)

        iGraph = InMemoryAggregatedGraph(graphs=[g])

        g = iGraph.get_context(identifier='urn:graph')
        self.assertEqual(len(g), 1)
        self.assertEqual(str(g.identifier), 'urn:graph')

    def testGetNonExistingContext(self):
        iGraph = InMemoryAggregatedGraph()

        g = iGraph.get_context(identifier='urn:graph')
        self.assertEqual(len(g), 0)
        self.assertEqual(str(g.identifier), 'urn:graph')


class InMemoryCopyOnEditAggregatedGraphTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


def main():
    unittest.main()


if __name__ == '__main__':
    main()
