import argparse
import sys
import os
from quit.conf import Feature, QuitStoreConfiguration
from quit.exceptions import InvalidConfigurationError
import rdflib.plugins.sparql
from rdflib.plugins.sparql.algebra import SequencePath
from rdflib.plugin import register
from rdflib.serializer import Serializer
from rdflib.query import Processor, UpdateProcessor, ResultSerializer
import logging

werkzeugLogger = logging.getLogger('werkzeug')
werkzeugLogger.setLevel(logging.INFO)

logger = logging.getLogger('quit')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
ch.setFormatter(formatter)


def initialize(args):
    """Build all needed objects.

    Returns:
        A dictionary containing the store object and git repo object.

    """
    if args['verbose']:
        ch.setLevel(logging.ERROR - args['verbose'] * 10)
        logger.addHandler(ch)

    logger.debug("Parsed args: {}".format(args))

    # add the handlers to the logger
    if args['logfile']:
        try:
            fh = logging.FileHandler(args['logfile'])
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            logger.debug("Logfile: {}".format(args['logfile']))
        except FileNotFoundError:
            logger.error("Logfile not found: {}".format(args['logfile']))
            sys.exit('Exiting quit')
        except PermissionError:
            logger.error("Can not create logfile: {}".format(args['logfile']))
            sys.exit('Exiting quit')

    # from Github: https://github.com/RDFLib/rdflib/issues/617
    # Egregious hack, the SequencePath object doesn't support compare, this implements the __lt__
    # method so that algebra.py works on sorting in SPARQL queries on e.g. rdf:List paths

    def sequencePathCompareLt(self, other):
        return str(self) < str(other)

    def sequencePathCompareGt(self, other):
        return str(self) < str(other)

    setattr(SequencePath, '__lt__', sequencePathCompareLt)
    setattr(SequencePath, '__gt__', sequencePathCompareGt)
    # End egregious hack

    # To get the best behavior, but still we have https://github.com/RDFLib/rdflib/issues/810
    rdflib.plugins.sparql.SPARQL_DEFAULT_GRAPH_UNION = args['defaultgraph_union']

    # To disable web access: https://github.com/RDFLib/rdflib/issues/810
    rdflib.plugins.sparql.SPARQL_LOAD_GRAPHS = False

    register(
        'sparql', Processor,
        'quit.tools.processor', 'SPARQLProcessor')

    register(
        'sparql', UpdateProcessor,
        'quit.tools.processor', 'SPARQLUpdateProcessor')

    register(
        'application/x-turtle', Serializer,
        'rdflib.plugins.serializers.turtle', 'TurtleSerializer')

    register(
        'application/xml', Serializer,
        'rdflib.plugins.serializers.rdfxml', 'XMLSerializer')

    register(
        'application/json', Serializer,
        'rdflib_jsonld.serializer', 'JsonLDSerializer')

    register(
        'application/trig', Serializer,
        'rdflib.plugins.serializers.trig', 'TrigSerializer')

    register(
        'application/xml', ResultSerializer,
        'rdflib.plugins.sparql.results.xmlresults', 'XMLResultSerializer')

    register(
        'application/json', ResultSerializer,
        'rdflib.plugins.sparql.results.jsonresults', 'JSONResultSerializer')

    register(
        'html', ResultSerializer,
        'quit.plugins.serializers.results.htmlresults', 'HTMLResultSerializer')

    register(
        'text/html', ResultSerializer,
        'quit.plugins.serializers.results.htmlresults', 'HTMLResultSerializer')

    register(
        'application/xhtml+xml', ResultSerializer,
        'quit.plugins.serializers.results.htmlresults', 'HTMLResultSerializer')

    register(
        'text/csv', ResultSerializer,
        'rdflib.plugins.sparql.results.csvresults', 'CSVResultSerializer')

    register(
        'application/sparql-results+xml', ResultSerializer,
        'rdflib.plugins.sparql.results.xmlresults', 'XMLResultSerializer')

    register(
        'application/sparql-results+json', ResultSerializer,
        'rdflib.plugins.sparql.results.jsonresults', 'JSONResultSerializer')

    try:
        config = QuitStoreConfiguration(
            configfile=args['configfile'],
            targetdir=args['targetdir'],
            upstream=args['repourl'],
            features=args['features'],
            namespace=args['namespace'],
            oauthclientid=args['oauth_clientid'],
            oauthclientsecret=args['oauth_clientsecret'],
        )
    except InvalidConfigurationError as e:
        logger.error(e)
        sys.exit('Exiting quit')

    # since repo is handled, we can add graphs to config

    logger.info('QuitStore Configuration initialized.')
    logger.debug('Path of Gitrepo: ' + config.getRepoPath())

    return config


class FeaturesAction(argparse.Action):
    """Actions that are executied for the configuration passed with the `--feature` option."""
    CHOICES = {
        'provenance': Feature.Provenance,
        'persistence': Feature.Persistence,
        'garbagecollection': Feature.GarbageCollection
    }

    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            flags = Feature.Unknown
            for value in values:
                if value not in self.CHOICES.keys():
                    message = ("invalid choice: {0!r} (choose from {1})".format(
                        value, ', '.join([repr(action) for action in self.CHOICES.keys()])))
                    raise argparse.ArgumentError(self, message)
                else:
                    flags |= self.CHOICES[value]

            setattr(namespace, self.dest, flags)


def getDefaults():
    return {
        'port': 5000,
        'host': '::',
        'logfile': None,
        'basepath': None,
        'namespace': 'http://quit.instance/',
        'targetdir': None,
        'repourl': None,
        'configfile': "config.ttl",
        'oauth_clientid': None,
        'oauth_clientsecret': None,
        'verbose': 0,
        'flask_debug': False,
        'defaultgraph_union': False,
        'features': 0
    }


def parseEnv():
    """Parse command line arguments.

    Returns:
        parsed object representing the config arguments.
    """

    env = {}
    if 'QUIT_PORT' in os.environ:
        env['port'] = os.environ['QUIT_PORT']

    if 'QUIT_LOGFILE' in os.environ:
        env['logfile'] = os.environ['QUIT_LOGFILE']

    if 'QUIT_BASEPATH' in os.environ:
        env['basepath'] = os.environ['QUIT_BASEPATH']

    if 'QUIT_NAMESPACE' in os.environ:
        env['namespace'] = os.environ['QUIT_NAMESPACE']

    if 'QUIT_TARGETDIR' in os.environ:
        env['targetdir'] = os.environ['QUIT_TARGETDIR']

    if 'QUIT_CONFIGFILE' in os.environ:
        env['configfile'] = os.environ['QUIT_CONFIGFILE']

    if 'QUIT_OAUTH_CLIENT_ID' in os.environ:
        env['oauth_clientid'] = os.environ['QUIT_OAUTH_CLIENT_ID']

    if 'QUIT_OAUTH_SECRET' in os.environ:
        env['oauth_clientsecret'] = os.environ['QUIT_OAUTH_SECRET']

    return env


def parseArgs(args):
    """Parse command line arguments.

    Returns:
        parsed object representing the config arguments.
    """
    basepathhelp = "Base path (aka. application root) (WSGI only)."
    featurehelp = """This option enables additional features of the QuitStore:
                "provenance" - Store provenance information for each revision.
                "persistance" - Store all internal data as rdf graph."""
    confighelp = """Path of config file (turtle). Defaults to ./config.ttl."""
    loghelp = """Path to the log file."""
    targethelp = 'The directory of the local store repository.'
    namespacehelp = """A base namespace that will be applied when dealing with relative URIs in
                    SPARQL UPDATE queries."""

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int)
    parser.add_argument('--host', type=str)
    parser.add_argument('-l', '--logfile', type=str, help=loghelp)
    parser.add_argument('-b', '--basepath', type=str, help=basepathhelp)
    parser.add_argument('-n', '--namespace', type=str, help=namespacehelp)
    parser.add_argument('-t', '--targetdir', type=str, help=targethelp)
    parser.add_argument('-r', '--repourl', type=str, help='A link/URI to a remote repository.')
    parser.add_argument('-c', '--configfile', type=str, help=confighelp)
    parser.add_argument('--oauth-clientid', type=str, dest='oauth_clientid')
    parser.add_argument('--oauth-clientsecret', type=str, dest='oauth_clientsecret')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('--flask-debug', action='store_true')
    parser.add_argument('--defaultgraph-union', action='store_true')
    parser.add_argument('-f', '--features', nargs='*', action=FeaturesAction,
                        default=Feature.Unknown,
                        help=featurehelp)

    logger.debug("Parsing args: {}".format(args))

    # Remove all values that received the default value None
    parsedArgs = {k: v for k, v in vars(parser.parse_args(args)).items() if v is not None}
    return parsedArgs
