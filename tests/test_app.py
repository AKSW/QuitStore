from context import quit
import os

from distutils.dir_util import copy_tree, remove_tree
from glob import glob
from os import remove, stat, path
from os.path import join, isdir
from quit import quit as quitApp
import unittest
import tempfile

class QuitAppTestCase(unittest.TestCase):

    def setUp(self):
        self.testData = './tests/samples/applicationTests'
        self.local = './tests/samples/local'
        self.remote = '.tests/samples/remote'
        self.logfile = '.tests/samples/quit.log'
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

        self.app = quitApp.app.test_client()

    def tearDown(self):
        def __deleteFiles(directory):
            files = glob(join(directory, '*'))
            for file in files:
                remove(file)

        __deleteFiles(self.local)
        __deleteFiles(self.remote)

        if os.path.isfile(self.logfile):
            remove(self.logfile)

        localGit = join(self.local, '.git')
        remoteGit = join(self.remote, '.git')

        if isdir(localGit):
            remove_tree(localGit)
        if isdir(remoteGit):
            remove_tree(remoteGit)

    def testStartApp(self):
        """Test start of quit store."""
        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        quitApp.initialize(args)

        query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"
        response = self.app.post('/sparql', data=dict(query=query))
        self.assertEqual(response.status, '200 OK')

    def testLogfileExists(self):
        """Test start of quit store with logfile."""
        self.assertFalse(os.path.isfile(self.logfile))

        args = quitApp.parseArgs([
            '-c',
            self.localConfigFile,
            '-cm',
            'localconfig',
            '-l',
            self.logfile
            ])

        quitApp.initialize(args)

        self.assertTrue(os.path.isfile(self.logfile))
        self.assertNotEqual(stat(self.logfile).st_size, 0)

        infomsg = 'QuitStore successfully running.'
        check = False

        if infomsg in open(self.logfile).read():
            check = True

        self.assertTrue(check)

    def testLogfileNotExists(self):
        """Test start of quit store without logfile."""
        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        quitApp.initialize(args)

        self.assertFalse(os.path.isfile(self.logfile))

    def testReloadStore(self):
        """Test reload of quit store."""
        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        quitApp.initialize(args)

        quitApp.reloadstore()

        query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"
        response = self.app.post('/sparql', data=dict(query=query))
        self.assertEqual(response.status, '200 OK')

    def testGitLog(self):
        """Test /git/log API request."""
        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        quitApp.initialize(args)

        response= self.app.get('/git/log')
        self.assertEqual(response.status, '200 OK')


if __name__ == '__main__':
    unittest.main()
