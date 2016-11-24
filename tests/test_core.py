#!/usr/bin/env python3

import unittest
from context import quit
from quit.core import MemoryStore, GitRepo
from os import path
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

    def testAddANewFile(self):
        repo = GitRepo(self.dir.name)

        testrepo = Repository(self.dir.name)

        self.file.write(b'Test')

        testrepo.index.read()
        self.assertEqual(len(testrepo.index), 0)

        repo.addfile(self.filename)

        index = testrepo.index
        index.read()

        p = index[self.filename].path

        self.assertEqual(path.join(self.dir.name, p), self.file.name)

    def testAddAExistingFile(self):
        repo = GitRepo(self.dir.name)

        testrepo = Repository(self.dir.name)

        self.file.write(b'Test')

        self.assertEqual(len(testrepo.index), 0)
        testrepo = None

        i = 0
        while(i<2):
            repo.addfile(self.filename)

            testrepo = Repository(self.dir.name)

            index = testrepo.index
            index.read()

            p = index[self.filename].path

            self.assertEqual(path.join(self.dir.name, p), self.file.name)
            self.assertEqual(len(testrepo.index), 1)

            testrepo = None
            i+=1

    def testCheckoutWithExistingCommitID(self):
        """Test if commits that exist, exist."""
        self.getrepowithcommit()
        repo = GitRepo(self.dir.name)
        testrepo = Repository(self.dir.name)

        self.assertEqual(len(repo.getcommits()), 1)

        id = repo.getcommits()[0]['id']

        self.file.seek(0, 0)
        self.assertEqual(self.file.readlines(), [b'First Line\n'])

        for commit in testrepo.walk(testrepo.head.target, GIT_SORT_REVERSE):
            self.assertEqual(str(id), str(commit.oid))

        # Write to file
        self.file.write(b'Second Line\n')
        self.file.read()
        index = testrepo.index
        index.add(self.filename)
        index.write()

        tree = index.write_tree()

        message = "Second commit of temporary test repo"
        newid = testrepo.create_commit('HEAD',
                                       self.author, self.comitter, message,
                                       tree,
                                       [testrepo.head.get_object().hex])

        self.file.seek(0, 0)
        self.assertEqual(self.file.readlines(), [b'First Line\n', b'Second Line\n'])

        repo = GitRepo(self.dir.name)
        repo.checkout(id)
        self.file.seek(0, 0)
        self.assertEqual(self.file.readlines(), [b'First Line\n'])

        repo.checkout(str(newid))
        self.file.seek(0, 0)
        self.assertEqual(self.file.readlines(), [b'First Line\n', b'Second Line\n'])

    def testCheckoutWithNonExistingCommitID(self):
        self.getrepowithcommit()
        repo = GitRepo(self.dir.name)

        testrepo = Repository(self.dir.name)

        self.assertEqual(len(repo.getcommits()), 1)
        id = repo.getcommits()[0]['id']

        repo.checkout(id)

        for commit in testrepo.walk(testrepo.head.target, GIT_SORT_REVERSE):
            self.assertEqual(str(id), str(commit.oid))

        self.assertNotEqual(str(id), 'committhatdoesnotexist')

        # Test
        repo.checkout('commitidthatdoesnotexist')

        for commit in testrepo.walk(testrepo.head.target, GIT_SORT_REVERSE):
            self.assertEqual(str(id), str(commit.oid))

    def testCommit(self):
        self.getrepowithaddedfile()

        repo = GitRepo(self.dir.name)

        repo.commit()

        testrepo = Repository(self.dir.name)
        commits = testrepo.walk(testrepo.head.target)
        self.assertEqual(len(list(commits)), 1)

        # Write to file
        self.file.write(b'Second Line\n')
        self.file.read()

        repo.commit('New commit from QuitTest')

        commits = testrepo.walk(testrepo.head.target)
        self.assertEqual(len(list(commits)), 2)

    def testCommitWithoutFileChanges(self):
        self.getrepowithcommit()

        repo = GitRepo(self.dir.name)

        testrepo = Repository(self.dir.name)
        commits = testrepo.walk(testrepo.head.target)
        self.assertEqual(len(list(commits)), 1)

        repo.commit()

        commits = testrepo.walk(testrepo.head.target)
        self.assertEqual(len(list(commits)), 1)

    def testGetTheGitLog(self):
        """Test the log."""
        repo = GitRepo(self.dir.name)
        log = repo.getcommits()
        self.assertTrue(len(log) == 0)

        self.getrepowithcommit()
        log = repo.getcommits()

        self.assertTrue(len(log) == 1)
        self.assertIsNotNone(log[0]['id'])
        self.assertIsNotNone(log[0]['commit_date'])
        self.assertEqual(log[0]['message'], 'First commit of temporary test repo')
        self.assertEqual(log[0]['author_email'], 'quit@quit.aksw.org')
        self.assertEqual(log[0]['parents'], [])
        self.assertEqual(log[0]['author_name'], 'QuitStoreTest')

    def testCommitExists(self):
        """Test if a commit exists."""
        self.getrepowithcommit()

        repo = GitRepo(self.dir.name)
        testrepo = Repository(self.dir.name)

        for commit in testrepo.walk(testrepo.head.target, GIT_SORT_TOPOLOGICAL):
            self.assertTrue(repo.commitexists(str(commit.oid)))

        self.assertFalse(repo.commitexists('foobar'))

    def testIsStagingAreaClean(self):
        self.getrepowithcommit()

        repo = GitRepo(self.dir.name)
        self.assertTrue(repo.isstagingareaclean())
        self.file.write(b'Changed file content\n')
        self.file.read()
        self.assertFalse(repo.isstagingareaclean())

    def testPullFromRemoteWhenAhead(self):
        self.getrepowithcommit()
        repo = GitRepo(self.dir.name)

        clone_repository(url=self.dir.name, path=self.remotedir.name, bare=True)

        repo.addremote('origin', self.remotedir.name)

        # Test if repos are equal
        localtest = Repository(self.dir.name)
        remotetest = Repository(self.remotedir.name)

        localids = []
        remoteids = []

        for commit in localtest.walk(localtest.head.target, GIT_SORT_TOPOLOGICAL):
            localids.append(commit.oid)

        for commit in remotetest.walk(remotetest.head.target, GIT_SORT_TOPOLOGICAL):
            remoteids.append(commit.oid)

        self.assertEqual(len(remoteids), 1)
        self.assertEqual(localids, remoteids)

        # Update local file and commit
        localfile = open(self.file.name, 'w')
        localfile.write('Change content in local file\n')
        localfile.close()
        repo.addall()
        repo.commit()

        repo.pull()

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
        self.getrepowithcommit()
        local = GitRepo(self.dir.name)

        clone_repository(url=self.dir.name, path=self.remotedir.name)

        local.addremote('origin', self.remotedir.name)
        # local.addremote('origin', 'git://github.com/nareike/adhs.git')
        remote = GitRepo(self.remotedir.name)

        # Test before repositories get diverged
        testlocal = Repository(self.dir.name)
        testremote = Repository(self.remotedir.name)

        locallog = []
        remotelog = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            locallog.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remotelog.append(commit.oid)

        self.assertEqual(locallog, remotelog)
        self.assertEqual(remotelog[0], locallog[0])

        remotefile = open(path.join(self.remotedir.name, self.filename), 'w')
        remotefile.write('Changed content in file\n')
        remotefile.close()
        remote.addall()
        remote.commit('Second commit in remote')

        locallog = []
        remotelog = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            locallog.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remotelog.append(commit.oid)

        self.assertEqual(remotelog[1], locallog[0])
        self.assertEqual(len(remotelog), 2)
        self.assertEqual(len(locallog), 1)

        local.pull()

        locallog = []
        remotelog = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            locallog.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remotelog.append(commit.oid)

        self.assertEqual(remotelog[0], locallog[0])
        self.assertEqual(remotelog[1], locallog[1])

    def testPushToRemoteWhenAhead(self):
        self.getrepowithcommit()
        repo = GitRepo(self.dir.name)

        clone_repository(url=self.dir.name, path=self.remotedir.name, bare=True)

        repo = GitRepo(self.dir.name)

        # Test before file gets changed
        testlocal = Repository(self.dir.name)
        testremote = Repository(self.remotedir.name)

        localids = []
        remoteids = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            localids.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remoteids.append(commit.oid)

        self.assertEqual(len(localids), 1)
        self.assertEqual(remoteids, localids)

        # Write file and create commit
        repo.addremote('test', self.remotedir.name)
        self.file.write(b'Add a second line to file\n')
        self.file.read()
        repo.addall()
        repo.commit()

        # Test after file got changed and commit was created
        repo.setpushurl('test', self.dir.name)
        repo.push(remote='test')

        localids = []
        remoteids = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            localids.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remoteids.append(commit.oid)

        self.assertEqual(len(localids), 2)
        self.assertEqual(localids, remoteids)

    def testPushToRemoteWhenDiverged(self):
        self.getrepowithcommit()
        local = GitRepo(self.dir.name)

        clone_repository(url=self.dir.name, path=self.remotedir.name)

        local.addremote('origin', self.remotedir.name)
        remote = GitRepo(self.remotedir.name)

        # Test before repositories will diverge
        testlocal = Repository(self.dir.name)
        testremote = Repository(self.remotedir.name)

        locallog = []
        remotelog = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            locallog.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remotelog.append(commit.oid)

        self.assertEqual(locallog, remotelog)

        # Update files and repositories
        remotefile = open(path.join(self.remotedir.name, path.basename(self.file.name)), 'w')
        remotefile.write('Add new content in remote file\n')
        remotefile.close()
        remote.addfile(self.filename)
        remote.addall()
        remote.commit()

        self.file.write(b'Add new content to local file\n')
        self.file.read()
        local.addall()
        local.commit()

        self.assertFalse(local.push())

        locallog = []
        remotelog = []

        for commit in testlocal.walk(testlocal.head.target, GIT_SORT_TOPOLOGICAL):
            locallog.append(commit.oid)

        for commit in testremote.walk(testremote.head.target, GIT_SORT_TOPOLOGICAL):
            remotelog.append(commit.oid)

        self.assertEqual(remotelog[1], locallog[1])
        self.assertNotEqual(remotelog[0], locallog[0])

    def testSuccessfullCommit(self):
        self.getrepowithaddedfile()

        repo = GitRepo(self.dir.name)
        repo.commit()

        testrepo = Repository(self.dir.name)
        commits = testrepo.walk(testrepo.head.target)
        self.assertEqual(len(list(commits)), 1)

        for commit in commits:
            self.assertEqual(commit.message, '\"New commit from quit-store\"')

    def testSuccessfullCommitWithMessage(self):
        self.getrepowithaddedfile()

        message = 'Test-Commit'

        repo = GitRepo(self.dir.name)
        repo.commit(message=message)

        testrepo = Repository(self.dir.name)
        commits = testrepo.walk(testrepo.head.target)
        self.assertEqual(len(list(commits)), 1)

        for commit in commits:
            self.assertEqual(commit.message, message)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
