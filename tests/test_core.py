#!/usr/bin/env python3

import unittest
from context import quit
from quit.core import MemoryStore, GitRepo
import quit.git
from os import path, environ
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from tempfile import TemporaryDirectory, NamedTemporaryFile

class MemoryStoreTests(unittest.TestCase):

    def setUp(self):
        self.dir = path.abspath('../sample')
        self.store = MemoryStore()
        self.store.addfile(path.join(self.dir, 'team.nq'), 'nq')

    def tearDown(self):
        self.store = None
        self.dir = None


class GitRepoTests(unittest.TestCase):

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

    def testCloneRepo(self):
        REMOTE_NAME = 'origin'
        REMOTE_URL = 'git://github.com/AKSW/QuitStore.example.git'

        dir = TemporaryDirectory()
        quit.git.Repository(dir.name, create=True, origin=REMOTE_URL)
        self.assertTrue(path.exists(path.join(dir.name, 'example.nq')))
        dir.cleanup()

    def testCloneRepoViaSSH(self):
        environ["QUIT_SSH_KEY_HOME"] = "./tests/assets/sshkey/"

        REMOTE_URL = 'git@github.com:AKSW/QuitStore.example.git'

        dir = TemporaryDirectory()
        quit.git.Repository(dir.name, create=True, origin=REMOTE_URL)
        self.assertTrue(path.exists(path.join(dir.name, 'example.nq')))
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

    def testCommit(self):
        """Test that adding data causes a new commit"""
        pass

    def testCommitMessages(self):
        """Test if setting a commit message works"""
        pass

    def testCommitDefaultMessages(self):
        """Test that a commit gets a default message"""
        pass

    def testCommitNoOp(self):
        """Test that adding an existing statement causes no new commit"""
        pass

    def testGetTheGitLog(self):
        """Test that it possible to get the git history"""
        pass

    def testGCConfiguration(self):
        """Test that the garbage collection works"""
        pass

    def testCommitExists(self):
        """Test that a commit exists after an update"""
        pass

    def testIsStagingAreaClean(self):
        """Test that the local staging area is clean after a commit"""
        pass

    def testPullFromRemoteWhenAhead(self):
        """Test that pulling from remote, when the local repos is ahead causes a merge"""
        pass

    def testPullFromRemoteWhenBehind(self):
        """Test that pulling from remote, when the local repos is behind causes a fast-forward"""
        pass

    def testPushToRemoteWhenAhead(self):
        """Test that pushing to remote, when the local repos is ahead updates the remote"""
        pass

    def testPushToRemoteWhenDiverged(self):
        """Test that pushing to remote, when the local repos is diverged does not kill the system"""
        pass

    def testRepoGarbageCollectionTrigger(self):
        self.getrepowithcommit()

        import os
        import stat
        import time
        with TemporaryDirectory() as execDir:
            execFile = os.path.join(execDir, "git")
            checkFile = os.path.join(execDir, "check")

            with open(execFile, 'w') as execFilePointer:
                execFilePointer.write("""#!/bin/sh
                if [ "$1" = "gc" ] ; then
                    touch """ + checkFile + """
                fi
                """)
            os.chmod(execFile, stat.S_IXUSR | stat.S_IRUSR)

            # configure PATH for Popen to contain dummy git gc, which should be triggered
            os.environ['PATH'] = ':'.join([execDir, os.getenv('PATH')])

            repo = GitRepo(self.dir.name)
            repo.garbagecollection()

            start = time.time()
            # check if mocked git was executed
            while not os.path.isfile(checkFile):
                if (time.time() - start) > 1:
                    self.fail("Git garbage collection was not triggered")

    def testSuccessfullCommitWithTime(self):
        """Test that two commits at different times actually have divverent timestamps."""
        # commit
        #time.sleep(1)
        # commit
        # self.assertNotEqual(commit.commit_time, lastCommit.commit_time)
        pass

def main():
    unittest.main()


if __name__ == '__main__':
    main()
