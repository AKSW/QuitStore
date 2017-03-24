#!/usr/bin/env python3
from os import listdir
from os.path import isdir, join, isfile, split, abspath, relpath
from pygit2 import Repository
from quit.exceptions import MissingConfigurationError, InvalidConfigurationError
from quit.exceptions import MissingFileError
from rdflib import Graph, URIRef
from rdflib.util import guess_format


class QuitConfiguration:
    """A class that keeps track of the relation between named graphs and files."""

    def __init__(self, configfile='config.ttl', gc=False, versioning=True):
        """The init method.

        This method checks if the config file is given and reads the config file.
        If the config file is missing, it will be generated after analyzing the
        file structure.
        """
        self.configchanged = False
        self.sysconf = Graph()
        self.versioning = versioning
        self.gc = gc
        self.origin = ''
        self.graphs = {}
        self.files = {}
        self.pathspec = []
        self.configfile = configfile

        if isfile(self.configfile):
            try:
                self.sysconf.parse(self.configfile, format='turtle')
            except:
                raise InvalidConfigurationError('Configuration could not be parsed', self.configfile)
        else:
            raise MissingConfigurationError('No store configuration found', self.configfile)

        self.__initfromconf()

        return

    def __initfromconf(self):
        """Read configuration from config file."""
        self.__setstoresettings()

        try:
            repo = Repository(self.gitrepo)
            self.storeinitialized = True
            self.setgraphs()
        except MissingFileError as e:
            raise MissingFileError(e)
        except:
            self.storeinitialized = False

        return

    def setgraphs(self, init=False):
        """Set all URIs and file paths of graphs that are configured in config.ttl."""
        nsQuit = 'http://quit.aksw.org'
        query = 'SELECT DISTINCT ?graphuri ?filename WHERE { '
        query+= '  ?graph a <' + nsQuit + '/Graph> . '
        query+= '  ?graph <' + nsQuit + '/graphUri> ?graphuri . '
        query+= '  ?graph <' + nsQuit + '/hasQuadFile> ?filename . '
        query+= '}'
        result = self.sysconf.query(query)

        changedfiles = {}
        for row in result:
            graphuri = str(row['graphuri'])
            filename = str(row['filename'])

            found = False

            absfile = abspath(filename)

            # Analyze and check files
            if absfile.startswith(self.gitrepo):
                # file is part of git repo
                if isfile(absfile):
                    # everything is fine
                    pass
                else:
                    try:
                        open(absfile, 'a').close()
                    except:
                        self.logger.debug('Can\'t create file in repo')
                        raise('Can\'t create file in repo')
                filename = relpath(self.gitrepo, absfile)
            else:
                joinedabsfile = abspath(join(self.gitrepo, filename))
                if joinedabsfile.startswith(self.gitrepo):
                    if isfile(joinedabsfile):
                        # everything is fine
                        pass
                    else:
                        try:
                            open(absfile, 'a').close()
                        except:
                            self.logger.debug('Cannot create file in repo')
                            raise MissingFileError('Cannot create file in repo')
                    filename = relpath(joinedabsfile, self.gitrepo)

            # we store which named graph is serialized in which file
            self.graphs[graphuri] = filename
            # and furthermore we assume that one file can contain data of more
            # than one named graph and so we store for each file a set of graphs
            if filename in self.files:
                self.files[filename]['graphs'].add(graphuri)
            else:
                fo = guess_format(filename)
                if fo is not None:
                    self.files[filename] = {
                        'serialization': fo,
                        'graphs': {graphuri}
                        }

        return

    def __setstoresettings(self):
        """Set the path of Git repository from configuration."""
        nsQuit = 'http://quit.aksw.org/'
        storeuri = URIRef('http://my.quit.conf/store')
        property = URIRef(nsQuit + 'pathOfGitRepo')

        for s, p, o in self.sysconf.triples((storeuri, property, None)):
            self.gitrepo = str(o)

        property = URIRef(nsQuit + 'origin')
        for s, p, o in self.sysconf.triples((storeuri, property, None)):
            self.origin = str(o)

        return

    def getrepopath(self):
        """Get the path of the git repo.

        Returns:
            A string containig the path of the git repo,
        """
        return self.gitrepo

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

    def getOrigin(self):
        """Get origin of store.

        Returns:
            A string containing the URL of the remote's origin
        """
        return self.origin

    def getpathspec(self):
        """Get pathspec from config."""
        return self.pathspec

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
            path = self.gitrepo
        files = [f for f in listdir(path) if isfile(join(path, f))]
        graphfiles = []
        for file in files:
            if guess_format(file) is not None:
                graphfiles.append(file)

        return graphfiles

    def isgarbagecollectionon(self):
        return self.gc

    def isversioningon(self):
        return self.versioning
