from context import quit
import os

from distutils.dir_util import copy_tree, remove_tree
from glob import glob
from os import remove, stat, path
from os.path import join, isdir
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Repository, Signature, init_repository
import quit.quit as quitApp
from quit.web.app import create_app
import unittest
import tempfile
import subprocess

class QuitAppTestCase(unittest.TestCase):

    author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
    comitter = Signature('QuitStoreTest', 'quit@quit.aksw.org')

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo = init_repository(self.tmpdir.name)
        self.testData = './tests/samples/applicationTests'
        self.local = './tests/samples/local'
        self.remote = '.tests/samples/remote'
        self.logfile = '.tests/samples/quit.log'
        copy_tree(self.testData, self.local)
        copy_tree(self.testData, self.remote)
        self.localConfigFile = join(self.local, 'config.ttl')
        self.remoteConfigFile = join(self.local, 'config.ttl')


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

        self.tmpdir.cleanup()
        self.tmpdir = None
        self.repo = None

    def setPathOfGitrepo(self, configfile, path):
        # with open(self.localConfigFile) as f:
        #     content = f.readlines()
        #
        # remove(configfile)
        repoline = '  <pathOfGitRepo>  "' + path + '" .'

        with open(configfile, 'w+') as f:
            # for line in content:
                line = f.readline()
                if line.startswith('  <pathOfGitRepo'):
                    f.write(repoline)
                else:
                    f.write(line)

    def initrepo(self):
        self.repo = Repository(self.tmpdir.name)

    def addfiles(self):
        """Create a repository and add a file to the git index."""
        # Add file to index
        self.initrepo()
        copy_tree(self.testData, self.tmpdir.name)
        index = self.repo.index
        index.read()
        index.add('example1.nq')
        index.add('example1.nq.graph')
        index.add('example2.nq')
        index.add('example2.nq.graph')
        index.write()

    def createcommit(self):
        """Prepare a git repository with one existing commit.

        Create a directory, initialize a git Repository, add
        and commit a file.

        Returns:
            A list containing the directory and file
        """
        self.addfiles()
        # Create commit
        index = self.repo.index
        index.read()
        tree = index.write_tree()
        message = "First commit of temporary test repo"
        self.repo.create_commit('HEAD',
                           self.author, self.comitter, message,
                           tree,
                           [])

    def testStartApp(self):
        """Test start of quit store."""

        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        objects = quitApp.initialize(args)

        config = objects['config']
        app = create_app(config).test_client()

        query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"
        response = app.post('/sparql', data=dict(query=query))
        self.assertEqual(response.status, '200 OK')

    def testReloadStore(self):
        """Test reload of quit store."""
        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        objects = quitApp.initialize(args)

        config = objects['config']
        app = create_app(config).test_client()

        app = create_app(config).test_client()

        query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"
        response = app.post('/sparql', data=dict(query=query))
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

        with open(self.logfile) as logFile:
            if infomsg in logFile.read():
                check = True

        self.assertTrue(check)

    def testLogfileNotExists(self):
        """Test start of quit store without logfile."""
        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        quitApp.initialize(args)

        self.assertFalse(os.path.isfile(self.logfile))

    def testCommits(self):
        """Test /commits API request."""

        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        objects = quitApp.initialize(args)

        config = objects['config']
        app = create_app(config).test_client()

        response = app.get('/commits')
        self.assertEqual(response.status, '200 OK')

    def testGCConfiguration(self):
        """Test Garbage Collection configuration."""
        args = quitApp.parseArgs(['-c', self.localConfigFile, '-gc'])
        quitApp.initialize(args)

        with subprocess.Popen(
            ["git", "config", "gc.auto"],
            stdout=subprocess.PIPE,
            cwd=self.local
        ) as getGCAuto:
            stdout, stderr = getGCAuto.communicate()
            response = stdout.decode("UTF-8").strip()

        self.assertNotEqual(response, '')
        self.assertEqual(response, '256')


if __name__ == '__main__':
    unittest.main()
