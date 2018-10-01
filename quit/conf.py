import logging

import os
from pygit2 import Repository
from os import walk
from os.path import join, isfile, relpath
from quit.exceptions import MissingConfigurationError, InvalidConfigurationError
from quit.exceptions import UnknownConfigurationError
from quit.helpers import isAbsoluteUri
from rdflib import Graph, ConjunctiveGraph, Literal, Namespace, URIRef, BNode
from rdflib.plugins.parsers import notation3
from rdflib.namespace import RDF, NamespaceManager
from rdflib.util import guess_format
from urllib.parse import quote, urlparse, urlencode
from uritools import urisplit

logger = logging.getLogger('quit.conf')


class Feature:
    Unknown = 0
    Provenance = 1 << 0
    Persistence = 1 << 1
    GarbageCollection = 1 << 2
    All = Provenance | Persistence | GarbageCollection


class QuitStoreConfiguration():
    """A class that provides information about settings, filesystem and git."""

    quit = Namespace('http://quit.aksw.org/vocab/')

    def __init__(
        self,
        configfile='config.ttl',
        features=None,
        upstream=None,
        targetdir=None,
        namespace=None
    ):
        """Initialize store configuration.

        This method checks if the config file is given and reads the config file.
        If the config file is missing, it will be generated after analyzing the
        file structure.
        """
        logger = logging.getLogger('quit.conf.QuitConfiguration')
        logger.debug('Initializing configuration object.')

        self.features = features
        self.configchanged = False
        self.sysconf = Graph()
        self.upstream = None
        self.namespace = None

        self.nsMngrSysconf = NamespaceManager(self.sysconf)
        self.nsMngrSysconf.bind('', self.quit, override=False)

        try:
            self.__initstoreconfig(
                namespace=namespace,
                upstream=upstream,
                targetdir=targetdir,
                configfile=configfile)
        except InvalidConfigurationError as e:
            logger.error(e)
            raise e

    def __initstoreconfig(self, namespace, upstream, targetdir, configfile):
        """Initialize store settings."""
        if isAbsoluteUri(namespace):
            self.namespace = namespace
        else:
            raise InvalidConfigurationError(
                "Quit expects an absolute http(s) base namespace, {} is not absolute.".format(
                    namespace))

        if configfile and isfile(configfile):
            try:
                self.sysconf.parse(configfile, format='turtle')
            except notation3.BadSyntax:
                raise InvalidConfigurationError(
                    "Bad syntax. Configuration file could not be parsed. {}".format(configfile)
                )
            except PermissionError:
                raise InvalidConfigurationError(
                    "Configuration file could not be parsed. Permission denied. {}".format(
                        configfile))
            except Exception as e:
                raise UnknownConfigurationError("UnknownConfigurationError: {}".format(e))

            self.configfile = configfile
        else:
            if not targetdir:
                raise InvalidConfigurationError('No target directory for git repo given')

        if targetdir:
            self.setRepoPath(targetdir)

        if upstream:
            self.setUpstream(upstream)

        return

    def hasFeature(self, flags):
        return flags == (self.features & flags)

    def getBindings(self):
        ns = Namespace('http://quit.aksw.org/vocab/')
        q = """SELECT DISTINCT ?prefix ?namespace WHERE {{
            {{
                ?ns a <{binding}> ;
                    <{predicate_prefix}> ?prefix ;
                    <{predicate_namespace}> ?namespace .
            }}
        }}""".format(
            binding=ns['Binding'], predicate_prefix=ns['prefix'],
            predicate_namespace=ns['namespace']
        )

        result = self.sysconf.query(q)
        return [(row['prefix'], row['namespace']) for row in result]

    def getDefaultBranch(self):
        """Get the default branch on the Git repository from configuration.

        Returns:
            A string containing the branch name.
        """
        nsQuit = 'http://quit.aksw.org/vocab/'
        storeuri = URIRef('http://my.quit.conf/store')
        property = URIRef(nsQuit + 'defaultBranch')

        for s, p, o in self.sysconf.triples((None, property, None)):
            return str(o)

        return "master"

    def getGlobalFile(self):
        """Get the graph file which should be used for unassigned graphs.

        Returns
            The filename of the graph file where unassigned graphs should be stored.

        """
        nsQuit = 'http://quit.aksw.org/vocab/'
        storeuri = URIRef('http://my.quit.conf/store')
        property = URIRef(nsQuit + 'globalFile')

        for s, p, o in self.sysconf.triples((None, property, None)):
            return str(o)

    def getRepoPath(self):
        """Get the path of Git repository from configuration.

        Returns:
            A string containig the path of the git repo.
        """
        nsQuit = 'http://quit.aksw.org/vocab/'
        storeuri = URIRef('http://my.quit.conf/store')
        property = URIRef(nsQuit + 'pathOfGitRepo')

        for s, p, o in self.sysconf.triples((None, property, None)):
            return str(o)

    def getUpstream(self):
        """Get the URI of Git remote from configuration."""
        nsQuit = 'http://quit.aksw.org/vocab/'
        storeuri = URIRef('http://my.quit.conf/store')
        property = self.quit.upstream

        for s, p, o in self.sysconf.triples((storeuri, property, None)):
            return str(o)

    def setUpstream(self, origin):
        self.sysconf.remove((None, self.quit.origin, None))
        self.sysconf.add((self.quit.Store, self.quit.upstream, Literal(origin)))

        return

    def setRepoPath(self, path):
        self.sysconf.remove((None, self.quit.pathOfGitRepo, None))
        self.sysconf.add((self.quit.Store, self.quit.pathOfGitRepo, Literal(path)))

        return


class QuitGraphConfiguration():
    """A class that keeps track of the relation between named graphs and files."""

    quit = Namespace('http://quit.aksw.org/vocab/')

    def __init__(self, repository):
        """Init graph configuration.

        This method checks if the config file is given and reads the config file.
        If the config file is missing, it will be generated after analyzing the
        file structure.
        """
        logger = logging.getLogger('quit.conf.QuitConfiguration')
        logger.debug('Initializing configuration object.')

        self.repository = repository
        self.configfile = None
        self.mode = None
        self.graphconf = None
        self.graphs = {}
        self.files = {}

    def initgraphconfig(self, rev):
        """Initialize graph settings.

        Public method to initalize graph settings. This method will be run only once.
        """
        if self.graphconf is None:
            self.graphconf = Graph()
            self.nsMngrGraphconf = NamespaceManager(self.graphconf)
            self.nsMngrGraphconf.bind('', self.quit, override=False)

        graph_files, config_files, rdf_files = self.get_blobs_from_repository(rev)

        if len(graph_files) == 0 and len(config_files) == 0:
            self.mode = 'graphfiles'
        elif len(graph_files) > 0 and len(config_files) > 0:
            raise InvalidConfigurationError(
                "Conflict. Found graphfiles and QuitStore configuration file.")
        elif len(graph_files) > 0:
            self.mode = 'graphfiles'
            self.__init_graph_conf_with_blobs(graph_files, rev)
        elif len(config_files) == 1:
            self.mode = 'configuration'
            self.__init_graph_conf_from_configuration(config_files[0], rdf_files)
        else:
            raise InvalidConfigurationError(
                "Conflict. Found more than one QuitStore configuration file.")

    def __init_graph_conf_with_blobs(self, files, rev):
        """Init a repository by analyzing all existing files."""
        for file, values in files.items():
            format = values[0]
            graphFileId = values[1]
            graphuri = URIRef(self.__get_uri_from_graphfile_blob(graphFileId))

            if graphuri and format == 'nquads':
                self.addgraph(file=file, graphuri=graphuri, format=format)
                self.graphs[graphuri] = file
                self.files[file] = {
                    'serialization': format, 'graphs': [graphuri], 'oid': files[file][1]}
            elif graphuri is None and format == 'nquads':
                tmpgraph = ConjunctiveGraph(identifier='default')

                try:
                    tmpgraph.parse(source=os.path.join(file), format=format)
                except Exception:
                    logger.error("Could not parse file {}. File skipped.".format(file))
                    continue

                namedgraphs = tmpgraph.contexts()
                founduris = []

                for graph in namedgraphs:
                    if not isinstance(graph, BNode) and str(graph.identifier) != 'default':
                        graphuri = graph.identifier
                        founduris.append(graphuri)

                if len(founduris) == 1:
                    self.addgraph(file=file, graphuri=graphuri, format=format)
                    self.graphs[graphuri] = file
                    self.files[file] = {
                        'serialization': format, 'graphs': [graphuri], 'oid': files[file][1]}
                elif len(founduris) > 1:
                    logger.info("No named graph found. {} skipped.".format(file))
                elif len(founduris) < 1:
                    logger.info(
                        "More than one named graphs found. Can't decide. {} skipped.".format(file))
            elif format == 'nt':
                if graphuri:
                    self.addgraph(file=file, graphuri=graphuri, format=format)
                    self.graphs[graphuri] = file
                    self.files[file] = {
                        'serialization': format, 'graphs': [graphuri], 'oid': files[file][1]}
                else:
                    logger.warning('No *.graph file found. ' + file + ' skipped.')

    def __init_graph_conf_from_configuration(self, configfileId, known_blobs):
        """Init graphs with setting from config.ttl."""
        try:
            configfile = self.repository.get(configfileId)
        except Exception as e:
            raise InvalidConfigurationError(
                "Blob for configfile with id {} not found in repository {}".format(configfileId, e))

        content = configfile.read_raw()

        try:
            self.graphconf.parse(data=content, format='turtle')
        except Exception as e:
            raise InvalidConfigurationError(
                "Configfile could not be parsed {} {}".format(configfileId, e)
            )
        nsQuit = 'http://quit.aksw.org/vocab/'
        query = 'SELECT DISTINCT ?graphuri ?filename ?format WHERE { '
        query += '  ?graph a <' + nsQuit + 'Graph> . '
        query += '  ?graph <' + nsQuit + 'graphUri> ?graphuri . '
        query += '  ?graph <' + nsQuit + 'graphFile> ?filename . '
        query += '  OPTIONAL { ?graph <' + nsQuit + 'hasFormat> ?format .} '
        query += '}'
        result = self.graphconf.query(query)

        for row in result:
            filename = str(row['filename'])
            if row['format'] is None:
                format = guess_format(filename)
            else:
                format = str(row['format'])
            if format not in ['nt', 'nquads']:
                break
            if filename not in known_blobs.keys():
                break

            graphuri = URIRef(str(row['graphuri']))

            # we store which named graph is serialized in which file
            self.graphs[graphuri] = filename
            self.files[filename] = {
                'serialization': format, 'graphs': [graphuri], 'oid': known_blobs[filename]}

    def __get_uri_from_graphfile_blob(self, oid):
        """Search for a graph uri in graph file and return it.

        Args
        ----
           oid: String oid of a graph file

        Returns
        -------
            graphuri: String with the graph URI

        """
        try:
            blob = self.repository.get(oid)
        except ValueError:
            logger.debug("Object with OID { } not found in repository.".format(oid))
            return

        content = blob.read_raw().decode().strip()

        try:
            urlparse(content)
        except Exception:
            logger.debug("No graph URI found in blob with OID {}.".format(oid))
            return

        return content

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

    def getgraphs(self):
        """Get all graphs known to conf.

        Returns
        -------
            A list containig all graph uris as string,

        """
        return self.graphs

    def getfiles(self):
        """Get all files known to conf.

        Returns
        -------
            A list containig all files as string,

        """
        return self.files

    def getfileforgraphuri(self, graphuri):
        """Get the file for a given graph uri.

        Args
        ----
            graphuri: A String of the named graph

        Returns
        -------
            A string of the path to the file asociated with named graph

        """
        if isinstance(graphuri, str):
            graphuri = URIRef(graphuri)

        if graphuri in self.graphs.keys():
            return self.graphs[graphuri]

        return

    def getgraphurifilemap(self):
        """Get the dictionary of graphuris and their files.

        Returns
        -------
            A dictionary of graphuris and information about their representation in repository.

        """
        return self.graphs

    def getserializationoffile(self, file):
        """Get the file for a given graph uri.

        Args
        ----
            file: A String of a file path

        Returns
        -------
            A string containing the RDF serialization of file

        """
        if file in self.files.keys():
            return self.files[file]['serialization']

        return

    def getgraphuriforfile(self, file):
        """Get the file for a given graph uri.

        Args
        ----
            file: A String of a file path

        Returns
        -------
            A set containing strings of graph uris asociated to that file

        """
        if file in self.files:
            return self.files[file]['graphs']

        return []

    def get_blobs_from_repository(self, rev):
        """Analyze all blobs of a revision.

        Returns
        -------
            A triple (dictionary, list, dictionary)
            dict: containg names of rdf-files plus their format and oid of graph file.
            list: containing names of config files.
            dict: containing names rdf files plus format and oid.

        """
        config_files = []
        graph_files = {}
        graph_file_blobs = {}
        rdf_file_blobs = {}
        try:
            commit = self.repository.revparse_single(rev)
        except Exception:
            return graph_files, config_files, rdf_file_blobs

        # Collect graph files, rdf files and config files
        for entry in commit.tree:
            if entry.type == 'blob':
                format = guess_format(entry.name)
                if format is None and entry.name.endswith('.graph'):
                    graph_file_blobs[entry.name] = entry.id
                elif format is not None and format in ['nquads', 'nt']:
                    rdf_file_blobs[entry.name] = (entry.id, format)
                elif format is not None and entry.name == 'config.ttl':
                    config_files.append(str(entry.id))

        # collect pairs of rdf files and graph files
        for filename in rdf_file_blobs.keys():
            if filename + '.graph' in graph_file_blobs.keys():
                graph_file_blob_id = graph_file_blobs[filename + '.graph']
                graph_files[filename] = (rdf_file_blobs[filename][1], str(graph_file_blob_id))

        return graph_files, config_files, rdf_file_blobs
