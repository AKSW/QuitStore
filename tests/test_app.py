from context import quit
import os

from distutils.dir_util import copy_tree, remove_tree
from glob import glob
from os import remove, stat
from os.path import join, isdir
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE, Repository, Signature, init_repository
import quit.quit as quitApp
from quit.web.app import create_app
import tempfile
import unittest


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

        with open(configfile, 'r') as f:
            content = f.readlines()

        with open(configfile, 'w') as f:
            for line in content:
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
        index.add('example2.nq')
        index.add('example2.nq.graph')
        index.add('example3.nq')
        index.add('config.ttl')
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
        self.repo.create_commit('HEAD', self.author, self.comitter, message, tree, [])

    def testEmptyGraphsOnStartup(self):
        """Test behaviour whith empty graphs."""
        def createFile(filepath, content=None):
            with open(filepath, 'a') as f:
                if content:
                    f.write(content)

        UPDATE = """INSERT DATA {{
            graph <{graph}> {{<urn:{seed}Sub> <urn:{seed}Pred> <urn:{seed}Obj> .}}
        }}"""

        DELETE = """DELETE WHERE {{
            graph <{graph}> {{ ?s ?p ?o .}}
        }}"""

        QUERY = {1: UPDATE, 2: UPDATE, 3: DELETE}

        SELECT = """
            SELECT ?s ?p ?o ?g
            WHERE {{
                graph ?g {{ ?s ?p ?o . }}
                FILTER (sameTerm(?g, <{graph}>))
            }}
            ORDER BY ?s ?p ?o
        """
        QUAD = "<urn:{seed}Sub> <urn:{seed}Pred> <urn:{seed}Obj> <{graph}> ."
        QUAD_CSV = "urn:{seed}Sub,urn:{seed}Pred,urn:{seed}Obj,{graph}"

        self.initrepo()
        index = self.repo.index
        fileA = 'graphA'
        fileB = 'graphB'
        files = [fileA, fileB]
        index.read()

        for file in files:
            createFile(
                join(self.tmpdir.name, file + '.nq')
            )
            createFile(
                join(self.tmpdir.name, file + '.nq.graph'),
                "http://ex.org/{}".format(file)
            )
            index.add(file + '.nq')
            index.add(file + '.nq.graph')
            index.add(file + '.nq.graph')

        index.write()
        tree = index.write_tree()
        message = "First commit of temporary test repo"
        self.repo.create_commit('HEAD', self.author, self.comitter, message, tree, [])

        args = quitApp.parseArgs(['-t', self.tmpdir.name, '-cm', 'graphfiles'])

        data = {'quit': {}, 'expected': {}}

        for run in [1, 2, 3]:
            # (Re)start quitApp after each run
            objects = quitApp.initialize(args)
            config = objects['config']
            app = create_app(config).test_client()
            data['quit'][run] = {}
            data['expected'][run] = {}

            # GET test values from quitApp and file system
            for file in files:
                data['quit'][run][file] = {}
                data['expected'][run][file] = {}

                # UPDATE/DELETE
                resp = app.post(
                    '/sparql',
                    data=dict(
                        query=QUERY[run].format(
                            graph="http://ex.org/" + file, seed='same{}'.format(run)
                            )
                        )
                )
                self.assertEqual(resp.status, '200 OK')

                # collect response data
                data['quit'][run][file]['response'] = app.post(
                    '/sparql',
                    data=dict(query=SELECT.format(graph='http://ex.org/' + file)),
                    headers={'Accept': 'text/csv'}
                ).data.decode('utf-8')

                # collect file content
                with open(join(self.tmpdir.name, file +'.nq'), 'r') as f:
                    data['quit'][run][file]['file_content'] = f.read()

            # SET expected values for each run
            if run == 1:
                for file in files:
                    data['expected'][run][file]['response'] = 's,p,o,g\r\n' + QUAD_CSV.format(
                        graph='http://ex.org/' + file, seed='same{}'.format(1)
                    ) + '\r\n'
                    data['expected'][run][file]['file_content'] = QUAD.format(
                        graph='http://ex.org/' + file, seed='same{}'.format(1)
                    )
            elif run == 2:
                for file in files:
                    data['expected'][run][file]['response'] = 's,p,o,g\r\n' + QUAD_CSV.format(
                        graph='http://ex.org/' + file, seed='same{}'.format(1)
                    ) + '\r\n' + QUAD_CSV.format(
                        graph='http://ex.org/' + file, seed='same{}'.format(2)
                    ) + '\r\n'
                    data['expected'][run][file]['file_content'] = QUAD.format(
                        graph='http://ex.org/' + file, seed='same{}'.format(1)
                    ) + '\n' + QUAD.format(
                        graph='http://ex.org/' + file, seed='same{}'.format(2)
                    )
            elif run == 3:
                for file in files:
                    data['expected'][run][file]['response'] = 's,p,o,g\r\n'
                    data['expected'][run][file]['file_content'] = ''

        # TEST
        for run in [1, 2, 3]:
            for file in files:
                self.assertEqual(
                    data['quit'][run][file]['file_content'],
                    data['expected'][run][file]['file_content']
                )
                self.assertEqual(
                    data['quit'][run][file]['response'],
                    data['expected'][run][file]['response']
                )

    def testVersioning(self):
        """
        Test quit with versioning.

        Compare the state (SPARQL query result, file content, commit messages) before and after an
        update query.
        """
        SELECT = """
            SELECT ?s ?p ?o
            WHERE {graph <http://example.org/1/> {?s ?p ?o .}}
            ORDER BY ?s ?p ?o
        """
        UPDATE = "INSERT DATA {graph <http://example.org/1/> {<newSub> <newPred> <newObj> .}}"
        COMMIT_MSG_INITIAL = 'First commit of temporary test repo'
        COMMIT_MSG_UPDATE= 'query: INSERT DATA {graph <http://example.org/1/>'
        COMMIT_MSG_UPDATE += ' {<newSub> <newPred> <newObj> .}}\n\nNew Commit from QuitStore'
        QRB = 's,p,o\r\n'
        QRB += 'http://example.org/Subject,http://example.org/Predicate,'
        QRB += 'http://example.org/Object\r\n'
        FCB = '<http://example.org/Subject> <http://example.org/Predicate>'
        FCB += ' <http://example.org/Object> <http://example.org/1/> .\n'
        QRA = QRB + 'newSub,newPred,newObj\r\n'
        FCA = FCB + '<newSub> <newPred> <newObj> <http://example.org/1/> .'

        self.setPathOfGitrepo(self.localConfigFile, self.tmpdir.name)

        self.createcommit()
        repo = Repository(self.tmpdir.name)

        commits_before = []

        # get commits before update query
        for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
            commits_before.append(commit.message)

        self.assertEqual(commits_before, [COMMIT_MSG_INITIAL])

        with open(join(self.tmpdir.name, 'example1.nq'), 'r') as f:
            file_content_before = f.read()
        self.assertEqual(FCB, file_content_before)

        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        objects = quitApp.initialize(args)

        config = objects['config']
        app = create_app(config).test_client()

        # get state before update query
        query_resp_before = app.post(
            '/sparql',
            data=dict(query=SELECT),
            headers={'Accept': 'text/csv'}
        ).data
        self.assertEqual(query_resp_before.decode('utf-8'), QRB)

        # update query
        update_resp = app.post('/sparql', data=dict(query=UPDATE))

        # get state after update query
        with open(join(self.tmpdir.name, 'example1.nq'), 'r') as f:
            file_content_after = f.read()
        self.assertEqual(FCA, file_content_after)

        query_resp_after = app.post(
            '/sparql',
            data=dict(query=SELECT),
            headers={'Accept': 'text/csv'}
        ).data
        self.assertEqual(query_resp_after.decode('utf-8'), QRA)

        commits_after = []
        for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL):
            commits_after.append(commit.message)
        self.assertEqual(commits_after, [COMMIT_MSG_UPDATE, COMMIT_MSG_INITIAL])

    def testContentNegotiation(self):
        """Test SPARQL with different Accept Headers."""
        query = 'SELECT * WHERE {graph ?g {?s ?p ?o .}} LIMIT 1'
        construct = 'CONSTRUCT {?s ?p ?o} WHERE {graph ?g {?s ?p ?o .}} LIMIT 1'
        self.setPathOfGitrepo(self.localConfigFile, self.tmpdir.name)
        self.createcommit()

        args = quitApp.parseArgs(
            ['-c', self.localConfigFile, '-cm', 'localconfig', '-f', 'provenance']
        )
        objects = quitApp.initialize(args)

        config = objects['config']
        app = create_app(config).test_client()

        test_values = {
            'sparql': [query, {
                    '*/*': 'application/sparql-results+xml',
                    'application/sparql-results+xml': 'application/sparql-results+xml',
                    'application/xml': 'application/xml',
                    'application/rdf+xml': 'application/rdf+xml',
                    'application/sparql-results+json': 'application/sparql-results+json',
                    'text/csv': 'text/csv',
                    'text/html': 'text/html',
                    'application/xhtml_xml': 'text/html'
                }
            ],
            'construct': [construct, {
                    '*/*': 'text/turtle',
                    'text/turtle': 'text/turtle',
                    'application/x-turtle': 'application/x-turtle',
                    'application/rdf+xml': 'application/rdf+xml',
                    'application/xml': 'application/xml',
                    'application/n-triples': 'application/n-triples',
                    'application/trig': 'application/trig'
                }
            ]
        }

        for ep_path in ['/sparql', '/provenance']:
            for query_type, values in test_values.items():
                query = values[0]

                # test supported
                for accept_type, content_type in values[1].items():
                    response = app.post(
                        ep_path,
                        data=dict(query=query),
                        headers={'Accept': accept_type}
                    )
                    self.assertEqual(response.status, '200 OK')
                    self.assertEqual(response.headers['Content-Type'], content_type)

                # test unsupported
                resp = app.post(ep_path, data=dict(query=query), headers={'Accept': 'foo/bar'})
                self.assertEqual(resp.status, '406 NOT ACCEPTABLE')

    def testStartApp(self):
        """Test start of quit store."""
        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        objects = quitApp.initialize(args)

        config = objects['config']
        app = create_app(config).test_client()

        query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"
        response = app.post('/sparql', data=dict(query=query))
        self.assertEqual(response.status, '200 OK')

    def testFeatureProvenance(self):
        """Test if feature is active or not."""
        query = "SELECT * WHERE {graph ?g {?s ?p ?o .}}"
        self.createcommit()
        args = quitApp.parseArgs(['-c', self.localConfigFile, '-cm', 'localconfig'])
        objects = quitApp.initialize(args)

        config = objects['config']
        app = create_app(config).test_client()
        response = app.post('/provenance', data=dict(query=query))
        self.assertEqual(response.status, '404 NOT FOUND')

        args = quitApp.parseArgs(
            ['-c', self.localConfigFile, '-cm', 'localconfig', '-f', 'provenance']
        )
        objects = quitApp.initialize(args)

        config = objects['config']
        app = create_app(config).test_client()

        response = app.post(
            '/provenance',
            data=dict(query=query)
        )
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

    def testInitWithGraphfiles(self):
        """Test quit with mode graphfiles."""
        query = "SELECT * WHERE {graph <http://example.org/1/> {?s ?p ?o .}} ORDER BY ?s ?p ?o"
        update = "INSERT DATA {graph <http://example.org/1/> {<newSub> <newPred> <newObj> .}}"
        self.setPathOfGitrepo(self.localConfigFile, self.tmpdir.name)

        self.createcommit()
        with open(join(self.tmpdir.name, 'example1.nq'), 'r') as f:
            file_example1_before = f.read()

        args = quitApp.parseArgs(['-t', self.tmpdir.name, '-cm', 'graphfiles'])
        objects = quitApp.initialize(args)
        config = objects['config']
        app = create_app(config).test_client()

        self.assertFalse(os.path.isfile(join(self.tmpdir.name, 'unassigned.nq')))

        # get state before update query
        query_resp_before = app.post(
            '/sparql',
            data=dict(query=query)
        ).data

        # update query
        update_resp = app.post('/sparql', data=dict(query=update))

        # get state after update query
        with open(join(self.tmpdir.name, 'example1.nq'), 'r') as f:
            file_example1_after = f.read()

        query_resp_after = app.post(
            '/sparql',
            data=dict(query=query)
        ).data

        self.assertNotEqual(file_example1_before, file_example1_after)
        self.assertNotEqual(query_resp_before, query_resp_after)


if __name__ == '__main__':
    unittest.main()
