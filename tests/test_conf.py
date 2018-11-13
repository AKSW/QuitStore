#!/usr/bin/env python3
import unittest
from context import quit
from glob import glob
from os import remove
from os.path import join, isdir
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from quit.conf import QuitStoreConfiguration, QuitGraphConfiguration
from quit.exceptions import MissingConfigurationError, InvalidConfigurationError
from quit.exceptions import MissingFileError
from distutils.dir_util import copy_tree, remove_tree
from helpers import TemporaryRepository, TemporaryRepositoryFactory
from tempfile import TemporaryDirectory, NamedTemporaryFile
import rdflib


class TestConfiguration(unittest.TestCase):
    ns = 'http://quit.instance/'

    def testNamespace(self):
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content1}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            good = ['http://example.org/thing#', 'https://example.org/', 'http://example.org/things/']
            bad = [None, 'file:///home/quit/', 'urn:graph/', 'urn:graph', '../test']

            # good base namespaces
            for uri in good:
                conf = QuitStoreConfiguration(targetdir=repo.workdir, namespace=uri)
                self.assertEqual(conf.namespace, uri)

            # bad base namespaces
            for uri in bad:
                with self.assertRaises(InvalidConfigurationError):
                    QuitStoreConfiguration(targetdir=repo.workdir, namespace=uri)

    def testStoreConfigurationWithDir(self):
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content1}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            conf = QuitStoreConfiguration(targetdir=repo.workdir, namespace=self.ns)
            self.assertEqual(conf.getRepoPath(), repo.workdir)
            self.assertEqual(conf.getDefaultBranch(), None)

    def testStoreConfigurationWithConfigfile(self):
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content1}
        with TemporaryRepositoryFactory().withGraphs(repoContent, 'configfile') as repo:
            conf = QuitStoreConfiguration(configfile=join(repo.workdir, 'config.ttl'), namespace=self.ns)
            self.assertEqual(conf.getRepoPath(), repo.workdir)
            self.assertEqual(conf.getDefaultBranch(), None)

    def testStoreConfigurationUpstream(self):
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content1}
        with TemporaryRepositoryFactory().withGraphs(repoContent, 'configfile') as repo:
            conf = QuitStoreConfiguration(
                configfile=join(repo.workdir, 'config.ttl'),
                upstream='http://cool.repo.git',
                namespace=self.ns)
            self.assertEqual(conf.getRepoPath(), repo.workdir)
            self.assertEqual(conf.getUpstream(), 'http://cool.repo.git')



    def testExistingRepoGraphFiles(self):
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content2 = '<urn:1> <urn:2> <urn:3> <http://example.org/> .\n'
        content2 += '<urn:a> <urn:b> <urn:c> <http://aksw.org/> .\n'
        repoContent = {'http://example.org/': content1, 'http://aksw.org/': content2}
        with TemporaryRepositoryFactory().withGraphs(repoContent) as repo:
            conf = QuitGraphConfiguration(repository=repo)
            conf.initgraphconfig('master')
            self.assertEqual(conf.mode, 'graphfiles')

            graphs = conf.getgraphs()
            self.assertEqual(
                sorted([str(x) for x in graphs]), ['http://aksw.org/', 'http://example.org/'])

            files = conf.getfiles()
            self.assertEqual(sorted(files), ['graph_0.nq', 'graph_1.nq'])

            serialization = conf.getserializationoffile('graph_0.nq')
            self.assertEqual(serialization, 'nquads')

            serialization = conf.getserializationoffile('graph_1.nq')
            self.assertEqual(serialization, 'nquads')
            gfMap = conf.getgraphurifilemap()

            self.assertEqual(gfMap, {
                    rdflib.term.URIRef('http://aksw.org/'): 'graph_0.nq',
                    rdflib.term.URIRef('http://example.org/'): 'graph_1.nq'
                })

            self.assertEqual(
                [str(x) for x in conf.getgraphuriforfile('graph_0.nq')],
                ['http://aksw.org/']
            )
            self.assertEqual(
                [str(x) for x in conf.getgraphuriforfile('graph_1.nq')],
                ['http://example.org/']
            )
            self.assertEqual(conf.getfileforgraphuri('http://aksw.org/'), 'graph_0.nq')
            self.assertEqual(conf.getfileforgraphuri('http://example.org/'), 'graph_1.nq')

    def testExistingRepoConfigfile(self):
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content2 = '<urn:1> <urn:2> <urn:3> <http://example.org/> .\n'
        content2 += '<urn:a> <urn:b> <urn:c> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content1, 'http://aksw.org/': content2}
        with TemporaryRepositoryFactory().withGraphs(repoContent, 'configfile') as repo:
            conf = QuitGraphConfiguration(repository=repo)
            conf.initgraphconfig('master')
            self.assertEqual(conf.mode, 'configuration')

            graphs = conf.getgraphs()
            self.assertEqual(sorted([str(x) for x in graphs]), ['http://aksw.org/', 'http://example.org/'])

            files = conf.getfiles()
            self.assertEqual(sorted(files), ['graph_0.nq', 'graph_1.nq'])

            serialization = conf.getserializationoffile('graph_0.nq')
            self.assertEqual(serialization, 'nquads')
            serialization = conf.getserializationoffile('graph_1.nq')
            self.assertEqual(serialization, 'nquads')

            gfMap = conf.getgraphurifilemap()
            self.assertEqual(gfMap, {
                    rdflib.term.URIRef('http://aksw.org/'): 'graph_0.nq',
                    rdflib.term.URIRef('http://example.org/'): 'graph_1.nq'
                })

            self.assertEqual(
                [str(x) for x in conf.getgraphuriforfile('graph_0.nq')],
                ['http://aksw.org/']
            )
            self.assertEqual(
                [str(x) for x in conf.getgraphuriforfile('graph_1.nq')], ['http://example.org/']
            )
            self.assertEqual(conf.getfileforgraphuri('http://aksw.org/'), 'graph_0.nq')
            self.assertEqual(conf.getfileforgraphuri('http://example.org/'), 'graph_1.nq')

    def testGraphConfigurationMethods(self):
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        content2 = '<urn:1> <urn:2> <urn:3> <http://example.org/> .\n'
        content2 += '<urn:a> <urn:b> <urn:c> <http://aksw.org/> .'
        repoContent = {'http://example.org/': content1, 'http://aksw.org/': content2}
        with TemporaryRepositoryFactory().withGraphs(repoContent, 'configfile') as repo:
            conf = QuitGraphConfiguration(repository=repo)
            conf.initgraphconfig('master')

            conf.removegraph('http://aksw.org/')

            self.assertEqual(conf.getgraphurifilemap(), {
                    rdflib.term.URIRef('http://example.org/'): 'graph_1.nq'})
            self.assertEqual(conf.getfileforgraphuri('http://aksw.org/'), None)
            self.assertEqual(conf.getgraphuriforfile('graph_0.nq'), [])
            self.assertEqual(conf.getserializationoffile('graph_0.nq'), None)

            conf.addgraph('http://aksw.org/', 'new_file.nq', 'nquads')

            self.assertEqual(conf.getgraphurifilemap(), {
                    rdflib.term.URIRef('http://aksw.org/'): 'new_file.nq',
                    rdflib.term.URIRef('http://example.org/'): 'graph_1.nq'})
            self.assertEqual(conf.getfileforgraphuri('http://aksw.org/'), 'new_file.nq')
            self.assertEqual(conf.getgraphuriforfile('new_file.nq'), ['http://aksw.org/'])
            self.assertEqual(conf.getserializationoffile('new_file.nq'), 'nquads')

    def testGraphConfigurationFailing(self):
        with TemporaryRepositoryFactory().withBothConfigurations() as repo:
            conf = QuitGraphConfiguration(repository=repo)
            self.assertRaises(InvalidConfigurationError, conf.initgraphconfig, 'master')

    def testWrongConfigurationFile(self):
        with TemporaryRepositoryFactory().withBothConfigurations() as repo:
            conf = QuitGraphConfiguration(repository=repo)
            self.assertRaises(InvalidConfigurationError, conf.initgraphconfig, 'master')

    def testNoConfigInformation(self):
        with TemporaryRepositoryFactory().withNoConfigInformation() as repo:
            conf = QuitGraphConfiguration(repository=repo)
            conf.initgraphconfig('master')
            self.assertEqual(conf.mode, 'graphfiles')


def main():
    unittest.main()


if __name__ == '__main__':
    main()
