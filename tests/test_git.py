#!/usr/bin/env python3

import unittest
from context import quit
import quit.git
from os import path, environ
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from tempfile import TemporaryDirectory, NamedTemporaryFile

class GitRevisionTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

class GitRepositoryTests(unittest.TestCase):

    def setUp(self):

        self.dir = TemporaryDirectory()
        self.remotedir = TemporaryDirectory()
        self.file = NamedTemporaryFile(dir=self.dir.name, delete=False)
        self.filename = path.basename(self.file.name)
        self.author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
        self.comitter = Signature('QuitStoreTest', 'quit@quit.aksw.org')

        # Initialize repository
        init_repository(self.dir.name, False)

    def tearDown(self):
        self.file = None
        self.filename = None
        self.dir.cleanup()
        self.dir = None
        self.remotedir.cleanup()
        self.remotedir = None

    def getrepowithaddedfile(self):
        """Create a repository and add a file to the git index."""
        # Write to file
        self.file.write(b'First Line\n')
        self.file.read()

        # Add file to index
        repo = Repository(self.dir.name)
        index = repo.index
        index.read()
        index.add(self.filename)
        index.write()

    def getrepowithcommit(self):
        """Prepare a git repository with one existing commit.

        Create a directory, initialize a git Repository, add
        and commit a file.

        Returns:
            A list containing the directory and file
        """
        self.getrepowithaddedfile()
        # Create commit
        repo = Repository(self.dir.name)
        index = repo.index
        index.read()
        tree = index.write_tree()
        message = "First commit of temporary test repo"
        repo.create_commit('HEAD',
                           self.author, self.comitter, message,
                           tree,
                           [])

    def testInitNotExistingsRepo(self):
        dir = TemporaryDirectory()

        repo = quit.git.Repository(self.dir.name)
        self.assertFalse(repo.is_bare)
        self.assertEqual(len(repo.revisions()), 0)

        dir.cleanup()

    def testInitEmptyRepo(self):
        self.getrepowithaddedfile()
        repo = quit.git.Repository(self.dir.name)
        self.assertFalse(repo.is_bare)
        self.assertEqual(len(repo.revisions()), 0)

    def testInitRepoWithExistingCommit(self):
        self.getrepowithcommit()
        repo = quit.git.Repository(self.dir.name)
        self.assertFalse(repo.is_bare)
        self.assertEqual(len(repo.revisions()), 1)

    def testCloneRepo(self):
        REMOTE_NAME = 'origin'
        REMOTE_URL = 'git://github.com/AKSW/QuitStore.example.git'

        dir = TemporaryDirectory()
        repo = quit.git.Repository(dir.name, create=True, origin=REMOTE_URL)
        self.assertTrue(path.exists(path.join(dir.name, 'example.nq')))
        self.assertFalse(repo.is_bare)
        dir.cleanup()

    def testCloneRepoViaSSH(self):
        environ["QUIT_SSH_KEY_HOME"] = "./tests/assets/sshkey/"

        REMOTE_URL = 'git@github.com:AKSW/QuitStore.example.git'

        dir = TemporaryDirectory()
        repo = quit.git.Repository(dir.name, create=True, origin=REMOTE_URL)
        self.assertTrue(path.exists(path.join(dir.name, 'example.nq')))
        self.assertFalse(repo.is_bare)
        dir.cleanup()

    def testCloneRepoViaSSHNoKeyFiles(self):
        environ["QUIT_SSH_KEY_HOME"] = "./tests/assets/nosshkey/"
        if "SSH_AUTH_SOCK" in environ:
            del environ["SSH_AUTH_SOCK"]

        REMOTE_URL = 'git@github.com:AKSW/QuitStore.example.git'

        dir = TemporaryDirectory()
        with self.assertRaises(Exception) as context:
            quit.git.Repository(dir.name, create=True, origin=REMOTE_URL)
        dir.cleanup()

    def testCloneNotExistingRepo(self):
        environ["QUIT_SSH_KEY_HOME"] = "./tests/assets/sshkey/"

        REMOTE_URL = 'git@github.com:AKSW/ThereIsNoQuitStoreRepo.git'

        dir = TemporaryDirectory()
        with self.assertRaises(Exception) as context:
            quit.git.Repository(dir.name, create=True, origin=REMOTE_URL)
        dir.cleanup()

    def testRepositoryIsEmpty(self):
        """Test that adding data causes a new commit."""
        self.getrepowithaddedfile()
        repo = quit.git.Repository(self.dir.name)
        self.assertTrue(repo.is_empty)

        self.getrepowithcommit()
        repo = quit.git.Repository(self.dir.name)
        self.assertFalse(repo.is_empty)

    def testRepositoryIsBare(self):
        """Test if is_bare is currently done in init/clone tests."""
        pass


def main():
    unittest.main()


if __name__ == '__main__':
    main()
