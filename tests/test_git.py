#!/usr/bin/env python3

import unittest
from context import quit
import quit.git
from quit.exceptions import QuitGitPushError
from os import path, environ
import pygit2
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from tempfile import TemporaryDirectory, NamedTemporaryFile
import subprocess
from helpers import TemporaryRepository, TemporaryRepositoryFactory


class GitRevisionTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass


class GitIndexTests(unittest.TestCase):

    def setUp(self):
        self.dir = TemporaryDirectory()
        self.file = NamedTemporaryFile(dir=self.dir.name, delete=False)
        self.filename = path.basename(self.file.name)
        self.author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
        self.comitter = Signature('QuitStoreTest', 'quit@quit.aksw.org')
        self.repo = quit.git.Repository(self.dir.name, create=True)

    def tearDown(self):
        self.file = None
        self.filename = None
        self.dir.cleanup()
        self.dir = None
        self.reop = None

    def addfile(self):
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
        self.repo = quit.git.Repository(self.dir.name)

    def createcommit(self):
        """Prepare a git repository with one existing commit.

        Create a directory, initialize a git Repository, add
        and commit a file.

        Returns:
            A list containing the directory and file
        """
        self.addfile()
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
        self.repo = quit.git.Repository(self.dir.name)

    def testIndexSetRevision(self):
        self.createcommit()
        reviosions = self.repo.revisions()
        index = quit.git.Index(self.repo)

        index.set_revision(reviosions[0].id)

        with self.assertRaises(Exception) as context:
            index.set_revision('not.existing.revision')

    def testIndexAddFile(self):
        index = quit.git.Index(self.repo)
        self.assertEqual(len(index.stash), 0)
        index.add(self.filename, b'First Line\n')
        self.assertEqual(len(index.stash), 1)

    def testIndexCommit(self):
        index = quit.git.Index(self.repo)

        self.assertFalse(index.dirty)

        commit = index.commit(
            "First commit from quit test",
            "QuitTest",
            "test@quitstore.example.org"
        )

        self.assertTrue(index.dirty)

        with self.assertRaises(Exception) as context:
            index.commit(
                "Second commit from quit test",
                "QuitTest",
                "test@quitstore.example.org"
            )


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

    def addfile(self):
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

    def createcommit(self):
        """Prepare a git repository with one existing commit.

        Create a directory, initialize a git Repository, add
        and commit a file.

        Returns:
            A list containing the directory and file
        """
        self.addfile()
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
        self.addfile()
        repo = quit.git.Repository(self.dir.name)
        self.assertFalse(repo.is_bare)
        self.assertEqual(len(repo.revisions()), 0)

    def testInitRepoWithExistingCommit(self):
        self.createcommit()
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

    def testPushRepo(self):
        """Test if it is possible to push to an empty remote repository."""
        with TemporaryRepository(True) as remote:
            graphContent = """
                <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."""
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

                quitRepo.push()

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)

    def testPushRepoNotConfiguredRemote(self):
        """Test if the push failes if the origin remote was not defined."""
        with TemporaryRepository(True) as remote:
            graphContent = """
                <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."""
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("upstream", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

                with self.assertRaises(QuitGitPushError):
                    quitRepo.push()

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

    def testPushRepoWithRemoteName(self):
        """Test if it is possible to push to a remote repository, which is not called orign."""
        with TemporaryRepository(True) as remote:
            graphContent = "<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("upstream", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

                quitRepo.push("upstream")

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)

    def testPushRepoNotConfiguredNamedRemote(self):
        """Test if the push failes if the specified remote was not defined."""
        with TemporaryRepository(True) as remote:
            graphContent = """
                <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."""
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

                with self.assertRaises(QuitGitPushError):
                    quitRepo.push("upstream")

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

    def testPushRepoWithDivergedRemote(self):
        """Test for an exception, if the local and remote repositories are diverged."""
        with TemporaryRepositoryFactory().withEmptyGraph("http://example.org/") as remote:
            graphContent = """
                <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> <http://example.org/> ."""
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)

                with self.assertRaises(pygit2.GitError):
                    quitRepo.push()

    def testRepositoryIsEmpty(self):
        """Test that adding data causes a new commit."""
        self.addfile()
        repo = quit.git.Repository(self.dir.name)
        self.assertTrue(repo.is_empty)

        self.createcommit()
        repo = quit.git.Repository(self.dir.name)
        self.assertFalse(repo.is_empty)

    def testRepositoryIsBare(self):
        """Test if is_bare is currently done in init/clone tests."""
        pass

    def testNoGCConfiguration(self):
        """Test Garbage Collection configuration."""
        quit.git.Repository(self.dir.name, garbageCollection=False)

        with subprocess.Popen(
            ["git", "config", "gc.auto"],
            stdout=subprocess.PIPE,
            cwd=self.dir.name
        ) as getGCAuto:
            stdout, stderr = getGCAuto.communicate()
            response = stdout.decode("UTF-8").strip()

        self.assertEqual(response, '')

    def testGCConfiguration(self):
        """Test Garbage Collection configuration."""
        quit.git.Repository(self.dir.name, garbageCollection=True)

        with subprocess.Popen(
            ["git", "config", "gc.auto"],
            stdout=subprocess.PIPE,
            cwd=self.dir.name
        ) as getGCAuto:
            stdout, stderr = getGCAuto.communicate()
            response = stdout.decode("UTF-8").strip()

        self.assertNotEqual(response, '')
        self.assertEqual(response, '256')


def main():
    unittest.main()


if __name__ == '__main__':
    main()
