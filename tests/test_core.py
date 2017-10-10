#!/usr/bin/env python3

import unittest
from context import quit
import quit.core
from os import path, environ
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from tempfile import TemporaryDirectory, NamedTemporaryFile


class QueryableTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


class StoreTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


class MemoryStoreTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass


class VirtualGraphTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


class QuitTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


class SeveralOldTest(unittest.TestCase):
    """Sort these test according to their corresponding classes."""
    def testCommit(self):
        """Test that adding data causes a new commit."""
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
        """Test that it possible to get the git history."""
        pass

    def testGCConfiguration(self):
        """Test that the garbage collection works."""
        pass

    def testCommitExists(self):
        """Test that a commit exists after an update."""
        pass

    def testIsStagingAreaClean(self):
        """Test that the local staging area is clean after a commit."""
        pass

    def testPullFromRemoteWhenAhead(self):
        """Test that pulling from remote, when the local repos is ahead causes a merge."""
        pass

    def testPullFromRemoteWhenBehind(self):
        """Test that pulling from remote, when the local repos is behind causes a fast-forward."""
        pass

    def testPushToRemoteWhenAhead(self):
        """Test that pushing to remote, when the local repos is ahead updates the remote."""
        pass

    def testPushToRemoteWhenDiverged(self):
        """Test that pushing to remote, when the local repos is diverged does not kill the system."""
        pass

    def testRepoGarbageCollectionTrigger(self):
        pass  # disable for now
        #self.getrepowithcommit()

        #import os
        #import stat
        #import time
        #with TemporaryDirectory() as execDir:
        #    execFile = os.path.join(execDir, "git")
        #    checkFile = os.path.join(execDir, "check")

        #    with open(execFile, 'w') as execFilePointer:
        #        execFilePointer.write("""#!/bin/sh
        #        if [ "$1" = "gc" ] ; then
        #            touch """ + checkFile + """
        #        fi
        #        """)
        #    os.chmod(execFile, stat.S_IXUSR | stat.S_IRUSR)

        #    # configure PATH for Popen to contain dummy git gc, which should be triggered
        #    os.environ['PATH'] = ':'.join([execDir, os.getenv('PATH')])

        #    repo = GitRepo(self.dir.name)
        #    repo.garbagecollection()

        #    start = time.time()
        #    # check if mocked git was executed
        #    while not os.path.isfile(checkFile):
        #        if (time.time() - start) > 1:
        #            self.fail("Git garbage collection was not triggered")

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
