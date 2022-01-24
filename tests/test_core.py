#!/usr/bin/env python3


import os
import stat
import time
import unittest
from context import quit
import quit.core
import quit.git
import quit.conf
from quit.graphs import InMemoryAggregatedGraph
from os import path, environ
from pygit2 import init_repository, Repository, clone_repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Signature
from rdflib import Graph, URIRef
from tempfile import TemporaryDirectory, NamedTemporaryFile
from helpers import TemporaryRepositoryFactory


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
    SELECT = """SELECT ?g ?s ?p ?o WHERE {GRAPH ?g {?s ?p ?o}}"""
    INSERT = """INSERT DATA {
                    GRAPH <urn:graph> {
                        <urn:A> <urn:B> <urn:C> .
                    }
                }"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testInsertIntoEmptyGraph(self):
        g = quit.core.VirtualGraph(
            InMemoryAggregatedGraph(
                graphs=[Graph()]
            )
        )

        g.update(self.INSERT)
        result = g.query(self.SELECT)

        resultCount = 0
        graphs = set()

        for r in result:
            graphs.add(str(r['g']))
            resultCount += 1

        self.assertEqual(resultCount, 1)
        self.assertIn('urn:graph', graphs)

    def testInsertIntoNonEmptyGraph(self):
        g = Graph(identifier='urn:existing.graph')
        g.add((URIRef('urn:1'), URIRef('urn:2'), URIRef('urn:3')))

        virtGraph = quit.core.VirtualGraph(
            InMemoryAggregatedGraph(
                graphs=[g]
            )
        )

        virtGraph.update(self.INSERT)
        result = virtGraph.query(self.SELECT)

        resultCount = 0
        graphs = set()

        for r in result:
            graphs.add(str(r['g']))
            resultCount += 1

        self.assertEqual(resultCount, 2)
        self.assertIn('urn:graph', graphs)
        self.assertIn('urn:existing.graph', graphs)


class QuitTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testDefaultGraph(self):
        content1 = '<urn:x> <urn:y> <urn:z> <http://example.org/> .'
        repoContent = {'http://example.org/': content1}
        with TemporaryRepositoryFactory().withGraphs(repoContent, 'configfile') as repo:
            conf = quit.conf.QuitStoreConfiguration(configfile=os.path.join(repo.workdir, 'config.ttl'), namespace='http://quit.instance/')
            quitInstance = quit.core.Quit(conf, quit.git.Repository(repo.path), None)
            self.assertTrue(quitInstance.getDefaultBranch() in ["main", "master"])


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

            with TemporaryDirectory() as repoDir:
                repository = quit.git.Repository(repoDir, create=True, garbageCollection=True)
                instance = quit.core.Quit(None, repository, None)
                instance.garbagecollection()

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
