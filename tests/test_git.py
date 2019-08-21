#!/usr/bin/env python3

import unittest
from context import quit
import quit.git
from quit.exceptions import QuitGitPushError, RevisionNotFound, RemoteNotFound, QuitMergeConflict
from os import path, environ
import pygit2
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from tempfile import TemporaryDirectory, NamedTemporaryFile
import subprocess
from helpers import createCommit, TemporaryRepository, TemporaryRepositoryFactory

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

        repo = quit.git.Repository(dir.name, create=True)
        self.assertFalse(repo.is_bare)
        self.assertEqual(len(repo.revisions()), 0)

        dir.cleanup()

    def testInitEmptyRepo(self):
        self.addfile()
        repo = quit.git.Repository(self.dir.name, create=True)
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
        self.assertTrue(path.exists(path.join(dir.name, 'example.nt')))
        self.assertTrue(path.exists(path.join(dir.name, 'example.nt.graph')))
        self.assertFalse(repo.is_bare)
        dir.cleanup()

    @unittest.skip("Currently fails on travis")
    def testCloneRepoViaSSH(self):
        environ["QUIT_SSH_KEY_HOME"] = "./tests/assets/sshkey/"

        REMOTE_URL = 'git@github.com:AKSW/QuitStore.example.git'

        dir = TemporaryDirectory()
        repo = quit.git.Repository(dir.name, create=True, origin=REMOTE_URL)
        self.assertTrue(path.exists(path.join(dir.name, 'example.nt')))
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
                <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

                quitRepo.push("origin", "master")

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)

    def testPushRefspecs(self):
        """Test if it is possible to push to an empty remote repository."""
        for refspec in [
            'master', 'refs/heads/master', 'refs/heads/master:master', 'master:master',
            'master:refs/heads/master', 'refs/heads/master:refs/heads/master'
        ]:
            with TemporaryRepository(True) as remote:
                graphContent = """
                    <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
                with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                    local.remotes.create("origin", remote.path)
                    quitRepo = quit.git.Repository(local.workdir)

                    self.assertTrue(remote.is_empty)
                    self.assertFalse(local.is_empty)

                    quitRepo.push("origin", refspec)

                    self.assertFalse(remote.is_empty)
                    self.assertFalse(local.is_empty)

    def testPushRepoNotConfiguredRemote(self):
        """Test if the push failes if the origin remote was not defined."""
        with TemporaryRepository(True) as remote:
            graphContent = """
                <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("upstream", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

                with self.assertRaises(RemoteNotFound):
                    quitRepo.push("origin", "master")

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

    def testPushRepoWithRemoteName(self):
        """Test if it is possible to push to a remote repository, which is not called orign."""
        with TemporaryRepository(True) as remote:
            graphContent = "<http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("upstream", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

                quitRepo.push("upstream", "master")

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)

    def testPushRepoNotConfiguredNamedRemote(self):
        """Test if the push failes if the specified remote was not defined."""
        with TemporaryRepository(is_bare=True) as remote:
            graphContent = """
                <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

                with self.assertRaises(RemoteNotFound):
                    quitRepo.push("upstream", "master")

                self.assertTrue(remote.is_empty)
                self.assertFalse(local.is_empty)

    def testPushRepoWithDivergedRemote(self):
        """Test for an exception, if the local and remote repositories are diverged."""
        with TemporaryRepositoryFactory().withEmptyGraph("http://example.org/") as remote:
            graphContent = """
                <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
            with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)

                with self.assertRaises(pygit2.GitError):
                    quitRepo.push("origin", "master")

    @unittest.skip("requires a remote with pre-receive hook")
    def testPushRepoWithRemoteReject(self):
        """Test for an exception, if the remote repositories rejects a push.

        CAUTION: This test is disabled, because it requires a remote with pre-receive hook.
        Unfortunately the libgit2 does not execute pre-receive hooks on local repositories.
        """
        graphContent = """
            <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as local:
            local.remotes.create("origin", "ssh://git@git.docker/testing.git")
            quitRepo = quit.git.Repository(local.workdir)

            self.assertFalse(local.is_empty)

            with self.assertRaises(QuitGitPushError):
                quitRepo.push()

    def testFetchRepo(self):
        """Test if it is possible to fetch from a remote repository."""
        graphContent = """
            <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryRepository(False) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertFalse(remote.is_empty)
                self.assertTrue(local.is_empty)
                self.assertTrue(quitRepo.is_empty)

                remoteHead = remote.revparse_single('HEAD').hex

                with self.assertRaises(RevisionNotFound):
                    quitRepo.revision('HEAD')

                quitRepo.fetch()

                self.assertEqual(quitRepo.revision('origin/master').id, remoteHead)

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)
                self.assertFalse(quitRepo.is_empty)

    def testFetchUpstreamRepo(self):
        """Test if it is possible to from from a remote, which set as upstream."""
        graphContent = """
            <http://ex.org/x> <http://ex.org/x> <http://ex.org/x> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryRepository(clone_from_repo=remote) as local:
                quitRepo = quit.git.Repository(local.workdir)

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)
                self.assertFalse(quitRepo.is_empty)

                with open(path.join(remote.workdir, "graph.nt"), "a") as graphFile:
                    graphContent = """
                        <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
                    graphFile.write(graphContent)

                createCommit(repository=remote)

                remoteHead = remote.revparse_single('HEAD').hex
                localHead = local.revparse_single('HEAD').hex

                self.assertNotEqual(localHead, remoteHead)

                quitRepo.fetch()

                self.assertEqual(quitRepo.revision('origin/master').id, remoteHead)

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)
                self.assertFalse(quitRepo.is_empty)

    def testPullRepo(self):
        """Test if it is possible to pull from a remote repository."""
        graphContent = """
            <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryRepository(False) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertFalse(remote.is_empty)
                self.assertTrue(local.is_empty)
                self.assertTrue(quitRepo.is_empty)

                remoteHead = remote.revparse_single('HEAD').hex

                with self.assertRaises(RevisionNotFound):
                    quitRepo.revision('HEAD')

                quitRepo.pull("origin", "master")

                self.assertEqual(quitRepo.revision('HEAD').id, remoteHead)

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)
                self.assertFalse(quitRepo.is_empty)

    def testPullRepoWithUnbornHead(self):
        """Test if it is possible to pull from a remote repository."""
        graphContent = """
            <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryRepository(False) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertFalse(remote.is_empty)
                self.assertTrue(local.is_empty)
                self.assertTrue(quitRepo.is_empty)

                remoteHead = remote.revparse_single('HEAD').hex

                with self.assertRaises(RevisionNotFound):
                    quitRepo.revision('HEAD')

                quitRepo.pull()

                self.assertEqual(quitRepo.revision('origin/master').id, remoteHead)

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)
                self.assertFalse(quitRepo.is_empty)

    def testPullRepoClonedNoChanges(self):
        """Test pull if both repos are at the same state."""
        graphContent = """
            <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryDirectory() as localDirectory:
                quitRepo = quit.git.Repository(localDirectory, create=True, origin=remote.path)

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

                remoteHead = remote.revparse_single('HEAD').hex

                self.assertEqual(quitRepo.revision('HEAD').id, remoteHead)

                quitRepo.pull("origin", "master")

                self.assertEqual(quitRepo.revision('HEAD').id, remoteHead)

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

    def testPullRepoClonedAndPullWithChanges(self):
        """Test clone, commit on remote and pull."""
        graphContent = """
            <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryDirectory() as localDirectory:
                quitRepo = quit.git.Repository(localDirectory, create=True, origin=remote.path)

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

                remoteHead = remote.revparse_single('HEAD').hex

                self.assertEqual(quitRepo.revision('HEAD').id, remoteHead)

                quitRepo.pull()

                self.assertEqual(quitRepo.revision('HEAD').id, remoteHead)

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

                remoteQuitRepo = quit.git.Repository(remote.workdir)
                index = remoteQuitRepo.index(remoteHead)
                graphContent += """
                    <http://ex.org/x> <http://ex.org/z> <http://ex.org/z> ."""
                index.add("graph.nt", graphContent)

                author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
                commitid = index.commit("from test", author.name, author.email)

                quitRepo.pull()

                self.assertEqual(quitRepo.revision('HEAD').id, str(commitid))

    def testPullRepoClonedAndPullWithThreeWayGitMerge(self):
        """Test clone, commit on remote and pull with merge, which resolves without conflicts."""
        graphContent = "<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> .\n"
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryDirectory() as localDirectory:
                quitRepo = quit.git.Repository(localDirectory, create=True, origin=remote.path)

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

                remoteHead = remote.revparse_single('HEAD').hex

                self.assertEqual(quitRepo.revision('HEAD').id, remoteHead)

                index = quitRepo.index(remoteHead)
                graph2Content = "<http://ex.org/x> <http://ex.org/y> <http://ex.org/y> .\n"
                index.add("graph2.nt", graph2Content)
                index.add("graph2.nt.graph", "http://example2.org/")
                author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
                localCommitid = index.commit("from local", author.name, author.email)
                quitRepo._repository.checkout_tree(quitRepo._repository.get(localCommitid))

                self.assertEqual(quitRepo.revision('HEAD').id, str(localCommitid))

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

                remoteQuitRepo = quit.git.Repository(remote.workdir)
                index = remoteQuitRepo.index(remoteHead)
                graphContent += "<http://ex.org/x> <http://ex.org/z> <http://ex.org/z> .\n"
                index.add("graph.nt", graphContent)
                remoteCommitid = index.commit("from remote", author.name, author.email)
                remoteQuitRepo._repository.checkout_tree(remoteQuitRepo._repository.get(remoteCommitid))

                quitRepo.pull(method="three-way-git")

                self.assertNotEqual(quitRepo.revision('HEAD').id, str(localCommitid))
                self.assertNotEqual(quitRepo.revision('HEAD').id, str(remoteCommitid))

                # check if head has local and remote commit id as ancestor
                self.assertListEqual([parent.id for parent in quitRepo.revision('HEAD').parents],
                                     [str(localCommitid), str(remoteCommitid)])

                # check if the merged commit contains all file contents
                with open(path.join(localDirectory, "graph.nt")) as f:
                    self.assertEqual("".join(f.readlines()), graphContent)

                with open(path.join(localDirectory, "graph2.nt")) as f:
                    self.assertEqual("".join(f.readlines()), graph2Content)

    def testPullRepoClonedAndPullWithThreeWayMerge(self):
        """Test clone, commit on remote and pull with merge, which resolves without conflicts."""
        graphContent = "<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> .\n"
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryDirectory() as localDirectory:
                quitRepo = quit.git.Repository(localDirectory, create=True, origin=remote.path)

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

                remoteHead = remote.revparse_single('HEAD').hex

                self.assertEqual(quitRepo.revision('HEAD').id, remoteHead)

                index = quitRepo.index(remoteHead)
                graph2Content = "<http://ex.org/x> <http://ex.org/y> <http://ex.org/y> .\n"
                index.add("graph2.nt", graph2Content)
                index.add("graph2.nt.graph", "http://example2.org/\n")
                author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
                localCommitid = index.commit("from local", author.name, author.email)
                quitRepo._repository.checkout_tree(quitRepo._repository.get(localCommitid))

                self.assertEqual(quitRepo.revision('HEAD').id, str(localCommitid))

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

                remoteQuitRepo = quit.git.Repository(remote.workdir)
                index = remoteQuitRepo.index(remoteHead)
                graphContent += "<http://ex.org/x> <http://ex.org/z> <http://ex.org/z> .\n"
                index.add("graph.nt", graphContent)
                remoteCommitid = index.commit("from remote", author.name, author.email)
                remoteQuitRepo._repository.checkout_tree(remoteQuitRepo._repository.get(remoteCommitid))

                quitRepo.pull(method="three-way")

                self.assertNotEqual(quitRepo.revision('HEAD').id, str(localCommitid))
                self.assertNotEqual(quitRepo.revision('HEAD').id, str(remoteCommitid))

                # check if head has local and remote commit id as ancestor
                self.assertListEqual([parent.id for parent in quitRepo.revision('HEAD').parents],
                                     [str(localCommitid), str(remoteCommitid)])

                # check if the merged commit contains all file contents
                with open(path.join(localDirectory, "graph.nt")) as f:
                    self.assertEqual("".join(f.readlines()), graphContent)

                with open(path.join(localDirectory, "graph2.nt")) as f:
                    self.assertEqual("".join(f.readlines()), graph2Content)

    def testPullRepoClonedAndPullWithConflict(self):
        """Test clone, commit on remote and pull with conflict."""
        graphContent = "<http://ex.org/a> <http://ex.org/b> <http://ex.org/c> .\n"
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryDirectory() as localDirectory:
                quitRepo = quit.git.Repository(localDirectory, create=True, origin=remote.path)

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

                remoteHead = remote.revparse_single('HEAD').hex

                self.assertEqual(quitRepo.revision('HEAD').id, remoteHead)

                index = quitRepo._repository.index
                with open(path.join(localDirectory, "graph.nt"), "a") as graphFile:
                    graphFile.write(
                        "<http://ex.org/x> <http://ex.org/y> <http://ex.org/y> .\n")
                index.add("graph.nt")
                index.write()
                tree = index.write_tree()

                author = Signature('QuitStoreTest', 'quit@quit.aksw.org')
                localCommitid = quitRepo._repository.create_commit(
                    'HEAD', author, author, "from local", tree, [remoteHead])

                self.assertFalse(remote.is_empty)
                self.assertFalse(quitRepo.is_empty)

                index = remote.index
                with open(path.join(remote.workdir, "graph.nt"), "a") as graphFile:
                    graphFile.write(
                        "<http://ex.org/x> <http://ex.org/z> <http://ex.org/z> .\n")
                index.add("graph.nt")
                index.write()
                tree = index.write_tree()
                remoteCommitid = remote.create_commit(
                    'HEAD', author, author, "from remote", tree, [remoteHead])

                remoteQuitRepo = quit.git.Repository(remote.workdir)

                with self.assertRaises(QuitMergeConflict):
                    quitRepo.pull(method="context")

                self.assertEqual(quitRepo.revision('HEAD').id, str(localCommitid))
                self.assertEqual(remoteQuitRepo.revision('HEAD').id, str(remoteCommitid))

    def testPullRepoFromNamedRemote(self):
        """Test if it is possible to pull from a remote repository, which is not called origin."""
        graphContent = """
            <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryRepository(False) as local:
                local.remotes.create("upstream", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertFalse(remote.is_empty)
                self.assertTrue(local.is_empty)
                self.assertTrue(quitRepo.is_empty)

                remoteHead = remote.revparse_single('HEAD').hex

                with self.assertRaises(RevisionNotFound):
                    quitRepo.revision('HEAD')

                quitRepo.pull(remote_name='upstream', refspec="master")

                self.assertEqual(quitRepo.revision('HEAD').id, remoteHead)

                self.assertFalse(remote.is_empty)
                self.assertFalse(local.is_empty)
                self.assertFalse(quitRepo.is_empty)

    def testPullRepoFromNotConfiguredRemote(self):
        """Test if it is possible to pull from a remote repository, which is not called origin."""
        graphContent = """
            <http://ex.org/x> <http://ex.org/y> <http://ex.org/z> ."""
        with TemporaryRepositoryFactory().withGraph("http://example.org/", graphContent) as remote:
            with TemporaryRepository(False) as local:
                local.remotes.create("origin", remote.path)
                quitRepo = quit.git.Repository(local.workdir)

                self.assertFalse(remote.is_empty)
                self.assertTrue(local.is_empty)
                self.assertTrue(quitRepo.is_empty)

                with self.assertRaises(RemoteNotFound):
                    quitRepo.pull(remote_name='upstream')

                self.assertFalse(remote.is_empty)
                self.assertTrue(local.is_empty)
                self.assertTrue(quitRepo.is_empty)

    def testPullRepoNoFFW(self):
        """TODO"""
        pass

    def testPullRepoFromMasterToDevelop(self):
        """TODO"""
        pass

    def testPullRepoFromDevelopToMaster(self):
        """TODO"""
        pass

    def testPullRepoFromRemoteTrackingBranch(self):
        """TODO"""
        pass

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
