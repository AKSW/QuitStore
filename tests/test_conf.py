#!/usr/bin/env python3
import unittest
from context import quit
from quit.conf import QuitConfiguration
from quit.exceptions import MissingConfigurationError, InvalidConfigurationError
from quit.exceptions import MissingFileError
from os import path
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from tempfile import TemporaryDirectory, NamedTemporaryFile


class TestConfiguration(unittest.TestCase):

    def setUp(self):
        self.dir = TemporaryDirectory()
        self.config = NamedTemporaryFile(suffix='.ttl', delete=False)
        self.file = NamedTemporaryFile(dir=self.dir.name, suffix='.nq')
        self.filename = path.basename(self.file.name)
        self.untrackedFile = NamedTemporaryFile(dir=self.dir.name, suffix='.nq')
        self.untrackedFilename = path.basename(self.untrackedFile.name)
        self.configContent = """
                    @base <http://quit.aksw.org/> .
                    @prefix conf: <http://my.quit.conf/> .
                    conf:store a <QuitStore> ;
                      <origin> "git://github.com/aksw/QuitStore.git" ;
                      <pathOfGitRepo> \"""" + self.dir.name + """\" .
                    conf:graph a <Graph> ;
                      <graphUri> <http://example.org/> ;
                      <hasQuadFile> \"""" + self.filename + '" . '

        self.config.write(bytes(self.configContent.encode('UTF-8')))
        self.config.seek(0)

    def tearDown(self):
        self.config = None
        self.file = None
        self.filename = None
        self.untrackedFile = None
        self.dir.cleanup()
        self.dir = None

    def testConfigParams(self):
        init_repository(self.dir.name, False)
        # no params given
        conf = QuitConfiguration(configfile=self.config.name)
        self.assertTrue(conf.isversioningon)
        self.assertTrue(conf.isgarbagecollectionon)

        # all params set
        conf = QuitConfiguration(gc=True, versioning=True, configfile=self.config.name)
        self.assertTrue(conf.isversioningon)
        self.assertTrue(conf.isgarbagecollectionon)

        # all params unset
        conf = QuitConfiguration(gc=False, versioning=False, configfile=self.config.name)
        self.assertTrue(conf.isversioningon)
        self.assertTrue(conf.isgarbagecollectionon)

    def testInitExistingFolder(self):
        conf = QuitConfiguration(configfile=self.config.name)
        self.assertEqual(conf.getrepopath(), self.dir.name)

    def testInitExistingRepo(self):
        init_repository(self.dir.name, False)
        conf = QuitConfiguration(configfile=self.config.name)
        self.assertEqual(conf.getrepopath(), self.dir.name)

    def testInitMissingConfiguration(self):
        init_repository(self.dir.name, False)

        with self.assertRaises(MissingConfigurationError):
            QuitConfiguration(configfile='no.config')

    def testInitGraphWithMissingFile(self):
        config = NamedTemporaryFile(suffix='.ttl', delete=False)
        configContent= self.configContent + """
                    conf:graph2 a <Graph> ;
                      <graphUri> <http://example2.org/> ;
                      <hasQuadFile> "nonexistingfile.nq" . """
        config.write(bytes(configContent.encode('UTF-8')))
        config.seek(0)

        init_repository(self.dir.name, False)

        conf = QuitConfiguration(configfile=config.name)

        files = conf.getfiles()
        self.assertEqual(sorted(files), sorted([self.filename, 'nonexistingfile.nq']))

    def testSysconfigValues(self):
        init_repository(self.dir.name, False)
        conf = QuitConfiguration(configfile=self.config.name)

        path = conf.getrepopath()
        self.assertEqual(path, self.dir.name)

        graphs = conf.getgraphs()
        self.assertEqual(graphs, ['http://example.org/'])

        files = conf.getfiles()
        self.assertEqual(files, [self.filename])

        serialization = conf.getserializationoffile(self.filename)
        self.assertEqual(serialization, 'nquads')

        gfMap = conf.getgraphurifilemap()
        self.assertEqual(gfMap, {'http://example.org/': self.filename})

        allFiles = conf.getgraphsfromdir()
        self.assertEqual(sorted(allFiles), sorted([self.filename, self.untrackedFilename]))

        self.assertEqual(conf.getOrigin(), 'git://github.com/aksw/QuitStore.git')
        self.assertEqual(conf.getgraphuriforfile(self.filename), ['http://example.org/'])
        self.assertEqual(conf.getfileforgraphuri('http://example.org/'), self.filename)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
