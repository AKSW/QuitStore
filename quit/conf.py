import logging
from os import listdir
from os.path import join, isfile, abspath, relpath
from quit.exceptions import MissingConfigurationError, InvalidConfigurationError
from rdflib import Graph, ConjunctiveGraph, Literal, Namespace, URIRef, BNode
from rdflib.namespace import RDF, NamespaceManager
from rdflib.util import guess_format
from urllib.parse import quote, urlparse

conflogger = logging.getLogger('conf.quit')
# create file handler which logs even debug messages
fh = logging.FileHandler('quit.log')
fh.setLevel(logging.DEBUG)
conflogger.addHandler(fh)


class QuitConfiguration:
    """A class that keeps track of the relation between named graphs and files."""

    def __init__(
        self,
        configmode=None,
        configfile='config.ttl',
        repository=None,
        targetdir=None,
        gc=False,
        versioning=True
    ):
        """The init method.

        This method checks if the config file is given and reads the config file.
        If the config file is missing, it will be generated after analyzing the
        file structure.
        """
        self.configchanged = False
        self.sysconf = Graph()
        self.graphconf = None
        self.versioning = versioning
        self.gc = gc
        self.origin = None
        self.graphs = {}
        self.files = {}

        self.quit = Namespace('http://quit.aksw.org/')
        self.nsMngrSysconf = NamespaceManager(self.sysconf)
        self.nsMngrSysconf.bind('', 'http://quit.aksw.org/', override=False)
        self.nsMngrGraphconf = NamespaceManager(self.sysconf)
        self.nsMngrGraphconf.bind('', 'http://quit.aksw.org/', override=False)

        self.__initstoreconfig(repository=repository, targetdir=targetdir, configfile=configfile, configmode=configmode)

        return

    def __initstoreconfig(self, repository=None, targetdir=None, configfile=None, configmode=None):
        """Initialize store settings."""
        if isfile(configfile):
            try:
                self.sysconf.parse(configfile, format='turtle')
            except:
                raise InvalidConfigurationError('Configuration could not be parsed', self.configfile)

            self.configfile = configfile
        else:
            if not targetdir:
                raise InvalidConfigurationError('No target directory for git repo given')

        if configmode:
            self.setConfigMode(configmode)

        if targetdir:
            self.setRepoPath(targetdir)

        if repository:
            self.setGitOrigin(repository)

        return

    def initgraphconfig(self):
        """Initialize graph settings.

        Public method to initalize graph settings. This method will be run only once.
        """
        if self.graphconf is None:
            self.__initgraphconfig()

    def __initgraphconfig(self, repository=None, targetdir=None):
        """Initialize graph settings."""
        self.graphconf = Graph()
        configmode = self.getConfigMode()

        if configmode == 'localconfig':
            self.__initgraphsfromconf(self.configfile)
        elif configmode == 'repoconfig':
            remConfigFile = join(self.getRepoPath(), 'config.ttl')
            self.__initgraphsfromconf(remConfigFile)
        elif configmode == 'graphfiles':
            self.__initgraphsfromdir(self.getRepoPath())
        else:
            raise InvalidConfigurationError('This mode is not supported.', self.configmode)
        return

    def __initgraphsfromdir(self, repodir):
        """Init a repository by analyzing all existing files."""
        graphs = self.getgraphsfromdir(repodir)

        for file, format in graphs.items():
            absfile = join(self.getRepoPath(), file)
            absgraphfile = absfile + '.graph'
            graphuri = self.__readGraphIriFile(absgraphfile)

            if graphuri and format == 'nquads':
                self.addgraph(file=file, graphuri=graphuri, format=format)
            elif graphuri is None and format == 'nquads':
                tmpgraph = ConjunctiveGraph(identifier='default')

                try:
                    tmpgraph.parse(source=absfile, format=format)
                except:
                    conflogger.warning('Could not parse graphfile ' + absfile + ' skipped.')
                    continue

                namedgraphs = tmpgraph.contexts()
                founduris = []

                for graph in namedgraphs:
                    if not isinstance(graph, BNode) and str(graph.identifier) != 'default':
                        graphuri = graph.identifier
                        founduris.append(graphuri)

                if len(founduris) == 1:
                    self.addgraph(file=file, graphuri=graphuri, format=format)
                elif len(founduris) > 1:
                    conflogger.warning('No named graph found. ' + absfile + ' skipped.')
                elif len(founduris) < 1:
                    conflogger.warning('More than one named graphs found. Can\'t decide. ' + absfile + ' skipped.')

            elif format == 'nt':
                if graphuri:
                    self.addgraph(file=file, graphuri=graphuri, format=format)
                else:
                    conflogger.warning('No .graph file found. ' + absfile + ' skipped.')

        self.__setgraphsfromconf()

    def __initgraphsfromconf(self, configfile):
        """Init graphs with setting from config.ttl."""
        if not isfile(configfile):
            raise MissingConfigurationError('Configfile is missing', configfile)

        try:
            self.graphconf.parse(configfile, format='turtle')
        except Exception as e:
            raise InvalidConfigurationError('Configfile could not be parsed', configfile, e)

        # Get Graphs
        self.__setgraphsfromconf()

    def __readGraphIriFile(self, graphfile):
        """Search for a graph uri in graph file and return it.

        Args:
            graphfile: String containing the path of a graph file

        Returns:
            graphuri: String with the graph URI
        """
        if isfile(graphfile):
            f = open(graphfile, 'r')
            graphuri = f.readline().strip()
            try:
                urlparse(graphuri)
            except:
                graphuri=None

            return graphuri

    def __setgraphsfromconf(self):
        """Set all URIs and file paths of graphs that are configured in config.ttl."""
        nsQuit = 'http://quit.aksw.org/'
        query = 'SELECT DISTINCT ?graphuri ?filename WHERE { '
        query+= '  ?graph a <' + nsQuit + 'Graph> . '
        query+= '  ?graph <' + nsQuit + 'graphUri> ?graphuri . '
        query+= '  ?graph <' + nsQuit + 'graphFile> ?filename . '
        query+= '}'
        result = self.graphconf.query(query)

        repopath = self.getRepoPath()

        changedfiles = {}
        for row in result:
            filename = str(row['filename'])
            format = guess_format(filename)
            if format not in ['nt', 'nquads']:
                break

            graphuri = str(row['graphuri'])

            found = False

            absfile = abspath(filename)
            joinedabsfile = abspath(join(repopath, filename))

            # Analyze and check files
            if absfile.startswith(repopath):
                # file is part of git repo
                if isfile(absfile):
                    # everything is fine
                    pass
                else:
                    try:
                        open(absfile, 'a').close()
                    except:
                        raise('Can\'t create file', absfile, 'in repo', self.getRepoPath())
                filename = relpath(repopath, absfile)
            else:
                if isfile(joinedabsfile):
                    # everything is fine
                    pass
                else:
                    try:
                        open(joinedabsfile, 'a').close()
                    except:
                        raise('Can\'t create file', absfile, 'in repo', self.getRepoPath())
                filename = relpath(joinedabsfile, repopath)

            # we store which named graph is serialized in which file
            self.graphs[graphuri] = filename
            # and furthermore we assume that one file can contain data of more
            # than one named graph and so we store for each file a set of graphs
            if filename in self.files:
                self.files[filename]['graphs'].add(graphuri)
            else:
                self.files[filename] = {
                    'serialization': format,
                    'graphs': {graphuri}
                    }

        return

    def addgraph(self, graphuri, file, format=None):
        self.graphconf.add((self.quit[quote(graphuri)], RDF.type, self.quit.Graph))
        self.graphconf.add((self.quit[quote(graphuri)], self.quit.graphUri, URIRef(graphuri)))
        self.graphconf.add((self.quit[quote(graphuri)], self.quit.graphFile, Literal(file)))
        if format is not None:
            self.graphconf.add((self.quit[quote(graphuri)], self.quit.hasFormat, Literal(format)))

        return

    def removegraph(self, graphuri):
        self.graphconf.remove((self.quit[urlencode(graphuri)], None, None))

        return

    def getConfigMode(self):
        """Get the mode how Quit-Store detects RDF files and named graphs.

        Returns:
            A string containig the mode.
        """
        nsQuit = 'http://quit.aksw.org/'
        property = URIRef(nsQuit + 'configMode')

        for s, p, o in self.sysconf.triples((None, property, None)):
            return str(o)

        return 'graphfiles'

    def getRepoPath(self):
        """Get the path of Git repository from configuration.

        Returns:
            A string containig the path of the git repo.
        """
        nsQuit = 'http://quit.aksw.org/'
        storeuri = URIRef('http://my.quit.conf/store')
        property = URIRef(nsQuit + 'pathOfGitRepo')

        for s, p, o in self.sysconf.triples((None, property, None)):
            return str(o)

    def getOrigin(self):
        """Get the URI of Git remote from configuration."""
        nsQuit = 'http://quit.aksw.org/'
        storeuri = URIRef('http://my.quit.conf/store')
        property = URIRef(nsQuit + 'origin')

        for s, p, o in self.sysconf.triples((storeuri, property, None)):
            return str(o)

    def getgraphs(self):
        """Get all graphs known to conf.

        Returns:
            A list containig all graph uris as string,
        """
        graphs = []
        for graph in self.graphs:
            graphs.append(graph)

        return graphs

    def getfiles(self):
        """Get all files known to conf.

        Returns:
            A list containig all files as string,
        """
        files = []
        for file in self.files:
            files.append(file)

        return files

    def getfileforgraphuri(self, graphuri):
        """Get the file for a given graph uri.

        Args:
            graphuri: A String of the named graph

        Returns:
            A string of the path to the file asociated with named graph
        """
        for uri, filename in self.graphs.items():
            if uri == graphuri:
                return filename

        return

    def getgraphurifilemap(self):
        """Get the dictionary of graphuris and their files.

        Returns:
            A dictionary of graphuris and information about their files.
        """

        return self.graphs

    def getserializationoffile(self, file):
        """Get the file for a given graph uri.

        Args:
            file: A String of a file path

        Returns:
            A string containing the RDF serialization of file
        """
        if file in self.files:
            return self.files[file]['serialization']

        return

    def getgraphuriforfile(self, file):
        """Get the file for a given graph uri.

        Args:
            file: A String of a file path

        Returns:
            A set containing strings of graph uris asociated to that file
        """
        if file in self.files:
            return list(self.files[file]['graphs'])

        return

    def getgraphsfromdir(self, path=None):
        """Get the files that are part of the repository (tracked or not).

        Returns:
            A list of filepathes.
        """
        if path is None:
            path = self.getRepoPath()
        files = [f for f in listdir(path) if isfile(join(path, f))]
        graphfiles = {}
        for file in files:
            format = guess_format(file)
            if format is not None:
                graphfiles[file] = format

        return graphfiles

    def isgarbagecollectionon(self):
        return self.gc

    def isversioningon(self):
        return self.versioning

    def setConfigMode(self, mode):
        self.sysconf.remove((None, self.quit.configMode, None))
        self.sysconf.add((self.quit.Store, self.quit.configMode, Literal(mode)))

        return

    def setGitOrigin(self, origin):
        self.sysconf.remove((None, self.quit.origin, None))
        self.sysconf.add((self.quit.Store, self.quit.origin, Literal(origin)))

        return

    def setRepoPath(self, path):
        self.sysconf.remove((None, self.quit.pathOfGitRepo, None))
        self.sysconf.add((self.quit.Store, self.quit.pathOfGitRepo, Literal(path)))

        return
