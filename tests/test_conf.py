#!/usr/bin/env python3
import unittest
from context import quit
from glob import glob
from os import remove
from os.path import join, isdir
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from quit.conf import QuitConfiguration
from quit.exceptions import MissingConfigurationError, InvalidConfigurationError
from quit.exceptions import MissingFileError
from distutils.dir_util import copy_tree, remove_tree
from tempfile import TemporaryDirectory, NamedTemporaryFile
import rdflib

class TestConfiguration(unittest.TestCase):

    def setUp(self):
        self.testData = './tests/samples/configuration_test'
        self.local = './tests/samples/local'
        self.remote = '.tests/samples/remote'
        copy_tree(self.testData, self.local)
        copy_tree(self.testData, self.remote)
        self.localConfigFile = join(self.local, 'config.ttl')
        self.remoteConfigFile = join(self.local, 'config.ttl')
        tempRepoLine = '  <pathOfGitRepo>  "' + self.local + '" .'

        with open(self.localConfigFile) as f:
            content = f.readlines()

        remove(self.localConfigFile)

        with open(self.localConfigFile, 'w+') as f:
            for line in content:
                if line.startswith('  <pathOfGitRepo'):
                    f.write(tempRepoLine)
                else:
                    f.write(line)

    def tearDown(self):
        def __deleteFiles(directory):
            files = glob(join(directory, '*'))
            for file in files:
                remove(file)

        __deleteFiles(self.local)
        __deleteFiles(self.remote)

        localGit = join(self.local, '.git')
        remoteGit = join(self.remote, '.git')

        if isdir(localGit):
            remove_tree(localGit)
        if isdir(remoteGit):
            remove_tree(remoteGit)

        return

    def testNamespace(self):
        init_repository(self.local, False)

        with self.assertRaises(InvalidConfigurationError):
            QuitConfiguration(configfile=self.localConfigFile, namespace='../')

        good = ['http://example.org/thing#', 'https://example.org/', 'http://example.org/things/']
        bad = ['file:///home/quit/', 'urn:graph/', 'urn:graph', '../test']

        for uri in good:
            conf = QuitConfiguration(configfile=self.localConfigFile, namespace=uri)
            self.assertEqual(conf.namespace, uri)

        for uri in bad:
            with self.assertRaises(InvalidConfigurationError):
                QuitConfiguration(configfile=self.localConfigFile, namespace=uri)

    def testInitExistingFolder(self):
        conf = QuitConfiguration(configfile=self.localConfigFile)
        self.assertEqual(conf.getRepoPath(), self.local)

    def testInitExistingRepo(self):
        init_repository(self.local, False)

        conf = QuitConfiguration(
            configfile=self.localConfigFile
        )

        conf.initgraphconfig()

        self.assertEqual(sorted(conf.getfiles()), ['example1.nq', 'example2.nt'])

        conf = QuitConfiguration(
            repository='assests/configuration_test',
            configfile=self.localConfigFile,
            configmode='repoconfig'
        )

        conf.initgraphconfig()

        self.assertEqual(sorted(conf.getfiles()), ['example1.nq', 'example2.nt'])

        conf = QuitConfiguration(
            configfile=self.localConfigFile,
            configmode='localconfig'
        )
        conf.initgraphconfig()

        self.assertEqual(sorted(conf.getfiles()), ['example1.nq', 'example2.nt'])

    def testInitMissingConfiguration(self):
        init_repository(self.local, False)

        with self.assertRaises(InvalidConfigurationError):
            QuitConfiguration(configfile='no.config')

    def testInitWithMissingGraphFiles(self):
        # Mode: fallback to graphfiles
        remove(join(self.local, 'example1.nq'))
        remove(join(self.local, 'example2.nt'))

        conf = QuitConfiguration(configfile=self.remoteConfigFile)
        conf.initgraphconfig()

        files = conf.getfiles()
        # no files to use
        self.assertEqual(sorted(files), [])

        # Mode: graphfiles
        conf = QuitConfiguration(
            configfile=self.localConfigFile,
            configmode='graphfiles'
        )
        conf.initgraphconfig()

        files = conf.getfiles()
        # no files to use
        self.assertEqual(sorted(files), [])

        # Mode: local config file
        conf = QuitConfiguration(
            configfile=self.remoteConfigFile,
            configmode='localconfig'
        )
        conf.initgraphconfig()

        files = conf.getfiles()
        # deleted files should be created
        self.assertEqual(sorted(files), ['example1.nq', 'example2.nt'])

        # Mode: remote config file
        remove(join(self.local, 'example1.nq'))
        remove(join(self.local, 'example2.nt'))

        conf = QuitConfiguration(
            repository='assests/configuration_test',
            configfile=self.localConfigFile,
            configmode='repoconfig'
        )
        conf.initgraphconfig()

        files = conf.getfiles()
        # deleted files should be created
        self.assertEqual(sorted(files), ['example1.nq', 'example2.nt'])


    def testStoreConfig(self):
        init_repository(self.local, False)
        conf = QuitConfiguration(configfile=self.localConfigFile)

        self.assertEqual(conf.getRepoPath(), self.local)
        self.assertEqual(conf.getOrigin(), 'git://github.com/aksw/QuitStore.git')

        allFiles = conf.getgraphsfromdir()
        self.assertEqual(sorted(allFiles), sorted(['config.ttl', 'example1.nq', 'example2.nt', 'example3.nq']))

    def testGraphConfigDefaultMode(self):
        conf = QuitConfiguration(
                    configfile=self.localConfigFile
                )

        conf.initgraphconfig()
        graphs = conf.getgraphs()
        self.assertEqual(sorted([str(x) for x in graphs]), ['http://example.org/2/', 'http://example.org/discovered/'])

        files = conf.getfiles()
        self.assertEqual(sorted(files), ['example1.nq', 'example2.nt'])

        serialization = conf.getserializationoffile('example1.nq')
        self.assertEqual(serialization, 'nquads')

        gfMap = conf.getgraphurifilemap()
        self.assertEqual(gfMap, {
                rdflib.term.URIRef('http://example.org/discovered/'): 'example1.nq',
                rdflib.term.URIRef('http://example.org/2/'): 'example2.nt'
            })

        self.assertEqual(
            [str(x) for x in conf.getgraphuriforfile('example1.nq')],
            ['http://example.org/discovered/']
        )
        self.assertEqual(
            [str(x) for x in conf.getgraphuriforfile('example2.nt')], ['http://example.org/2/']
        )
        self.assertEqual(conf.getfileforgraphuri('http://example.org/discovered/'), 'example1.nq')
        self.assertEqual(conf.getfileforgraphuri('http://example.org/2/'), 'example2.nt')

    def testGraphConfigLocalConfig(self):
        conf = QuitConfiguration(
                    configmode='localconfig',
                    configfile=self.localConfigFile
                )

        conf.initgraphconfig()
        graphs = conf.getgraphs()
        self.assertEqual(sorted([str(x) for x in graphs]), ['http://example.org/1/', 'http://example.org/2/'])

        files = conf.getfiles()
        self.assertEqual(sorted(files), ['example1.nq', 'example2.nt'])

        serialization = conf.getserializationoffile('example1.nq')
        self.assertEqual(serialization, 'nquads')

        gfMap = conf.getgraphurifilemap()
        self.assertEqual(gfMap, {
                rdflib.term.URIRef('http://example.org/1/'): 'example1.nq',
                rdflib.term.URIRef('http://example.org/2/'): 'example2.nt'
            })

        self.assertEqual([str(x) for x in conf.getgraphuriforfile('example1.nq')], ['http://example.org/1/'])
        self.assertEqual([str(x) for x in conf.getgraphuriforfile('example2.nt')], ['http://example.org/2/'])
        self.assertEqual(conf.getfileforgraphuri('http://example.org/1/'), 'example1.nq')
        self.assertEqual(conf.getfileforgraphuri('http://example.org/2/'), 'example2.nt')

    def testGraphConfigRemoteConfig(self):
        conf = QuitConfiguration(
                    configmode='repoconfig',
                    configfile=self.localConfigFile
                )

        conf.initgraphconfig()
        graphs = conf.getgraphs()
        self.assertEqual(sorted([str(x) for x in graphs]), ['http://example.org/1/', 'http://example.org/2/'])

        files = conf.getfiles()
        self.assertEqual(sorted(files), ['example1.nq', 'example2.nt'])

        serialization = conf.getserializationoffile('example1.nq')
        self.assertEqual(serialization, 'nquads')

        gfMap = conf.getgraphurifilemap()
        self.assertEqual(gfMap, {
                rdflib.term.URIRef('http://example.org/1/'): 'example1.nq',
                rdflib.term.URIRef('http://example.org/2/'): 'example2.nt'
            })

        self.assertEqual([str(x) for x in conf.getgraphuriforfile('example1.nq')], ['http://example.org/1/'])
        self.assertEqual([str(x) for x in conf.getgraphuriforfile('example2.nt')], ['http://example.org/2/'])
        self.assertEqual(conf.getfileforgraphuri('http://example.org/1/'), 'example1.nq')
        self.assertEqual(conf.getfileforgraphuri('http://example.org/2/'), 'example2.nt')

    def testGraphConfigGraphFiles(self):
        conf = QuitConfiguration(
                    configmode='graphfiles',
                    configfile=self.localConfigFile
                )

        conf.initgraphconfig()
        graphs = conf.getgraphs()
        self.assertEqual(sorted([str(x) for x in graphs]), ['http://example.org/2/', 'http://example.org/discovered/'])

        files = conf.getfiles()
        self.assertEqual(sorted(files), ['example1.nq', 'example2.nt'])

        serialization = conf.getserializationoffile('example1.nq')
        self.assertEqual(serialization, 'nquads')

        gfMap = conf.getgraphurifilemap()
        self.assertEqual(gfMap, {
                rdflib.term.URIRef('http://example.org/discovered/'): 'example1.nq',
                rdflib.term.URIRef('http://example.org/2/'): 'example2.nt'
            })

        self.assertEqual([str(x) for x in conf.getgraphuriforfile('example1.nq')], ['http://example.org/discovered/'])
        self.assertEqual([str(x) for x in conf.getgraphuriforfile('example2.nt')], ['http://example.org/2/'])
        self.assertEqual(conf.getfileforgraphuri('http://example.org/discovered/'), 'example1.nq')
        self.assertEqual(conf.getfileforgraphuri('http://example.org/2/'), 'example2.nt')

def main():
    unittest.main()


if __name__ == '__main__':
    main()
