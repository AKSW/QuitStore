#!/usr/bin/env python3

import unittest
from context import MemoryStore, GitRepo
from os import path
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL
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
        dir = TemporaryDirectory()
        init_repository(dir.name)
        file = NamedTemporaryFile(dir=dir.name, delete=False)
        self.file = file
        self.dir = dir
        self.remotedir = TemporaryDirectory()

    def addfiletorepo(self):
        """
            Create a directory, initialize a git Repository and add
            a file to the git index.
        """
        dir = self.dir
        file = self.file

        repo = GitRepo(dir.name)

        file.write(b'Test\n')
        file.read()

        repo.addfile(file.name)

        self.file = file
        self.dir = dir

    def createcommit(self):
        """Prepare a git repository with one existing commit.

        Create a directory, initialize a git Repository, add
        and commit a file.

        Returns:
            A list containing the directory and file
        """
        self.addfiletorepo()

        dir = self.dir
        file = self.file

        repo = GitRepo(dir.name)
        repo.commit()

        self.file = file
        self.dir = dir

    def tearDown(self):
        self.file = None
        self.dir.cleanup()
        self.remotedir.cleanup()

    def testAddANewFile(self):
        dir = self.dir
        file = self.file

        repo = GitRepo(dir.name)

        testrepo = Repository(dir.name)

        file.write(b'Test')

        self.assertEqual(len(testrepo.index), 0)
        testrepo = None

        self.assertTrue(repo.addfile(file.name))

        testrepo = Repository(dir.name)

        index = testrepo.index
        index.read()

        p = index[path.basename(file.name)].path

        self.assertEqual(path.join(dir.name, p), file.name)

    def testAddAExistingFile(self):
        dir = self.dir
        file = self.file

        repo = GitRepo(dir.name)

        testrepo = Repository(dir.name)

        file.write(b'Test')

        self.assertEqual(len(testrepo.index), 0)
        testrepo = None

        i = 0
        while(i<2):
            repo.addfile(file.name)

            testrepo = Repository(dir.name)

            index = testrepo.index
            index.read()

            p = index[path.basename(file.name)].path

            self.assertEqual(path.join(dir.name, p), file.name)
            self.assertEqual(len(testrepo.index), 1)

            testrepo = None
            i+=1

        file = None
        dir = None

    def testCheckoutWithNonExistingCommitID(self):
        self.createcommit()
        dir = self.dir

        repo = GitRepo(dir.name)
        testrepo = Repository(dir.name)
        log = repo.getcommits()
        currentid = log[0]['id']

        # Test
        repo.checkout('foobar')

        for commit in testrepo.walk(testrepo.head.target, GIT_SORT_TOPOLOGICAL):
            self.assertEqual(currentid, str(commit.oid))

    def testCheckoutWithExistingCommitID(self):
        """Test if commits that exist, exist."""
        self.addfiletorepo()
        dir = self.dir
        file = self.file

        repo = GitRepo(dir.name)
        testrepo = Repository(dir.name)

        # We are at HEAD now
        filecontent = {}
        lines = []
        file.seek(0)

        # save file content
        for line in file.readlines():
            lines.append(line.decode('UTF-8'))

        # compare file content
        self.assertEqual(lines, ['Test\n'])

        filecontent[1] = lines

        # Update file and create the 2nd commit
        file.write(b'Add a second line to file\n')
        file.seek(0)
        lines = []
        # save file content
        for line in file.readlines():
            lines.append(line.decode('UTF-8'))

        # compare file content
        self.assertEqual(lines, ['Test\n', 'Add a second line to file\n'])

        filecontent[0] = lines
        repo.update()
        repo.commit('Added a line to ' + file.name)

        # Test if file content from above is equal to that we get if we checkout
        # the correspinding commit
        i = 0
        for commit in testrepo.walk(testrepo.head.target, GIT_SORT_TOPOLOGICAL):
            repo.checkout(str(commit.oid))
            testfile = open(file.name, 'r')
            self.assertEqual(filecontent[i], testfile.readlines())
            testfile.close()
            i+= 1

    def testClearStagingArea(self):
        self.createcommit()
        dir = self.dir
        file = self.file
        repo = GitRepo(dir.name)
        file.seek(0)
        line = file.read()
        self.assertEqual(line, b'Test\n')
        self.assertTrue(repo.isstagingareaclean())

    def testCommitWithoutChanges(self):
        self.addfiletorepo()
        dir = self.dir

        repo = GitRepo(dir.name)

        i = 0

        while i<2:
            # Commit
            repo.commit()

            # Test
            testrepo = Repository(dir.name)
            commits = testrepo.walk(testrepo.head.target)
            self.assertEqual(len(list(commits)), 1)
            testrepo = None
            i+=1

    def testIfExistingCommitExists(self):
        """Test if commits that exist, exist."""
        self.createcommit()
        dir = self.dir

        repo = GitRepo(dir.name)
        testrepo = Repository(dir.name)

        for commit in testrepo.walk(testrepo.head.target, GIT_SORT_TOPOLOGICAL):
            self.assertTrue(repo.commitexists(str(commit.oid)))

    def testGetTheEmptyGitLog(self):
        """Test the log if no commit exists."""
        self.addfiletorepo()
        dir = self.dir
        file = self.file
        repo = GitRepo(dir.name)
        log = repo.getcommits()
        self.assertTrue(len(log) == 0)

    def testGetTheGitLog(self):
        """Test the log with one existing commit."""
        self.createcommit()
        dir = self.dir
        file = self.file
        repo = GitRepo(dir.name)
        log = repo.getcommits()
        self.assertTrue(len(log) == 1)

    def getGitDirectoryWith2ExistingCommits(self):
        """Prepare a git repository with one existing commit.

        Create a directory, initialize a git Repository, add
        and commit a file.

        Returns:
            A list containing the directory and file
        """
        self.addfiletorepo()
        dir = self.dir
        file = self.file

        repo = GitRepo(dir.name)
        repo.commit()
        file.write(b'Add a second line to file\n')
        file.read()
        repo.update()
        repo.commit()

        return(dir, file)

    def testIfNonExistingCommitExists(self):
        """Test if a commit that doesn't exist, exists."""
        self.createcommit()
        dir = self.dir
        file = self.file

        repo = GitRepo(dir.name)
        self.assertFalse(repo.commitexists('foobar'))

    def testIsNonClearStaginAreaClear(self):
        self.createcommit()
        dir = self.dir
        file = self.file
        repo = GitRepo(dir.name)
        file.write(b'Changed file content\n')
        file.read()
        self.assertFalse(repo.isstagingareaclean())

    def testPullFromRemoteWhenAhead(self):
        self.createcommit()
        dir = self.dir
        file = self.file
        repo = GitRepo(dir.name)
        remotedir = self.remotedir

        remote = clone_repository(url=dir.name, path=remotedir.name, bare=True)

        repo = GitRepo(dir.name)
        repo.addremote('test', remotedir.name)

        # Test if repos are equal
        localtest = Repository(dir.name)
        remotetest = Repository(remotedir.name)

        localids = []
        remoteids = []

        for commit in localtest.walk(localtest.head.target, GIT_SORT_TOPOLOGICAL):
            localids.append(commit.oid)

        for commit in remotetest.walk(remotetest.head.target, GIT_SORT_TOPOLOGICAL):
            remoteids.append(commit.oid)

        self.assertEqual(len(remoteids), 1)
        self.assertEqual(localids, remoteids)

        self.assertFalse(repo.pull(remote='test'))

        # Update local file and commit
        file.write(b'Add a second line to file\n')
        file.read()
        repo.update()
        repo.commit()

        self.assertFalse(repo.pull(remote='test'))

        localids = []
        remoteids = []

        for commit in localtest.walk(localtest.head.target, GIT_SORT_TOPOLOGICAL):
            localids.append(commit.oid)

        for commit in remotetest.walk(remotetest.head.target, GIT_SORT_TOPOLOGICAL):
            remoteids.append(commit.oid)

        self.assertEqual(len(localids), 2)
        self.assertEqual(len(remoteids), 1)
        self.assertEqual(localids[1], remoteids[0])

    def testPullFromRemoteWhenBehind(self):
        self.createcommit()
        dir = self.dir
        file = self.file
        local = GitRepo(dir.name)
        remotedir = self.remotedir
        # Copy repo to add a remote
        # self.copytree(dir.name, newdir.name, symlinks=True)

        clone_repository(url=dir.name, path=remotedir.name)

        local.addremote('origin', remotedir.name)
        remote = GitRepo(remotedir.name)

        # Test before repositories get diverged
        testlocal = Repository(dir.name)
        testremote = Repository(remotedir.name)

        locallog = []
        remotelog = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            locallog.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remotelog.append(commit.oid)

        self.assertEqual(locallog, remotelog)

        remotefile = open(path.join(remotedir.name, path.basename(file.name)), 'w')
        remotefile.write('A new line in remote file\n')
        remotefile.close()
        remote.addfile(path.join(remotedir.name, path.basename(file.name)))
        remote.update()
        remote.commit()

        self.assertTrue(local.pull())

        locallog = []
        remotelog = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            locallog.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remotelog.append(commit.oid)

        # Base should be the same
        self.assertEqual(remotelog[0], locallog[0])
        self.assertEqual(remotelog[1], locallog[1])
        # HEAD should not

    def testPushToRemoteWhenAhead(self):
        self.createcommit()
        dir = self.dir
        file = self.file
        repo = GitRepo(dir.name)
        remotedir = self.remotedir
        # Copy repo to add a remote
        # self.copytree(dir.name, newdir.name, symlinks=True)

        remote = clone_repository(url=dir.name, path=remotedir.name, bare=True)

        repo = GitRepo(dir.name)
        testrepo = Repository(dir.name)

        # Test before file gets changed
        testlocal = Repository(dir.name)
        testremote = Repository(remotedir.name)

        localids = []
        remoteids = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            localids.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remoteids.append(commit.oid)

        self.assertEqual(len(localids), 1)
        self.assertEqual(remoteids, localids)

        # Write file and create commit
        repo.addremote('test', remotedir.name)
        file.write(b'Add a second line to file\n')
        file.read()
        repo.update()
        repo.commit()

        # Test after file got changed and commit was created
        self.assertTrue(repo.push(remote='test'))

        localids = []
        remoteids = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            localids.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remoteids.append(commit.oid)

        self.assertEqual(len(localids), 2)
        self.assertEqual(localids, remoteids)

    def testPushToRemoteWhenDiverged(self):
        self.createcommit()
        dir = self.dir
        file = self.file
        local = GitRepo(dir.name)
        remotedir = self.remotedir

        clone_repository(url=dir.name, path=remotedir.name)

        local.addremote('origin', remotedir.name)
        remote = GitRepo(remotedir.name)

        # Test before repositories will diverge
        testlocal = Repository(dir.name)
        testremote = Repository(remotedir.name)

        locallog = []
        remotelog = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            locallog.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remotelog.append(commit.oid)

        self.assertEqual(locallog, remotelog)

        # Update files and repositories
        remotefile = open(path.join(remotedir.name, path.basename(file.name)), 'w')
        remotefile.write('A new line in remote file\n')
        remotefile.close()
        remote.addfile(path.join(remotedir.name, path.basename(file.name)))
        remote.update()
        remote.commit()

        file.write(b'Change local file\n')
        file.read()
        local.update()
        local.commit()

        # Test again with diverged repositories
        # Push should fail
        self.assertFalse(local.push())

        locallog = []
        remotelog = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            locallog.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remotelog.append(commit.oid)

        # Base should be the same
        self.assertEqual(remotelog[1], locallog[1])
        # HEAD shouldn't
        self.assertNotEqual(remotelog[0], locallog[0])

    def testSuccessfullCommit(self):
        self.addfiletorepo()
        dir = self.dir

        repo = GitRepo(dir.name)

        # Commit
        self.assertTrue(repo.commit())

        # Test
        testrepo = Repository(dir.name)
        commits = testrepo.walk(testrepo.head.target)
        self.assertEqual(len(list(commits)), 1)

        for commit in commits:
            self.assertEqual(commit.message, '\"New commit from quit-store\"')

    def testSuccessfullCommitWithMessage(self):
        self.addfiletorepo()
        dir = self.dir

        message = 'Test-Commit'

        repo = GitRepo(dir.name)

        # Commit
        self.assertTrue(repo.commit(message=message))

        # Test
        testrepo = Repository(dir.name)
        commits = testrepo.walk(testrepo.head.target)
        self.assertEqual(len(list(commits)), 1)

        for commit in commits:
            self.assertEqual(commit.message, message)

    def testUpdateWithSeveralChangedFiles(self):
        self.assertTrue(True)

    def testUpdateWithUnchangedStagingArea(self):
        self.assertTrue(True)

def main():
    unittest.main()

if __name__ == '__main__':
    main()
