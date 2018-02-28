import argparse
import sys
import os
from quit.conf import Feature, QuitConfiguration
from quit.exceptions import InvalidConfigurationError
from quit.web.app import create_app
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
    if args.verbose:
        ch.setLevel(logging.INFO)
        logger.addHandler(ch)
        logger.debug('Loglevel: INFO')

    if args.verboseverbose:
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        logger.debug('Loglevel: DEBUG')

    logger.debug("Parsed args: {}".format(args))

    # add the handlers to the logger

    if args.logfile:
        try:
            fh = logging.FileHandler(args.logfile)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            logger.debug("Logfile: {}".format(args.logfile))
        except FileNotFoundError:
            logger.error("Logfile not found: {}".format(args.logfile))
            sys.exit('Exiting quit')
        except PermissionError:
            logger.error("Can not create logfile: {}".format(args.logfile))
            sys.exit('Exiting quit')

    if args.garbagecollection:
        logger.info(
            "Please use the option \"--feature garbagecollection\" instead of "
            + "\"-gc\" or \"--garbagecollection\"."
        )
        args.features |= Feature.GarbageCollection

    try:
        config = QuitConfiguration(
            configfile=args.configfile,
            targetdir=args.targetdir,
            repository=args.repourl,
            configmode=args.configmode,
            features=args.features,
            oauthclientid=args.oauth_clientid,
            oauthclientsecret=args.oauth_clientsecret,
        )
    except InvalidConfigurationError as e:
        logger.error(e)
        sys.exit('Exiting quit')

    # since repo is handled, we can add graphs to config
    config.initgraphconfig()

    logger.info('QuitStore successfully running.')
    logger.info('Known graphs: ' + str(config.getgraphs()))
    logger.info('Known files: ' + str(config.getfiles()))
    logger.debug('Path of Gitrepo: ' + config.getRepoPath())
    logger.debug('Config mode: ' + str(config.getConfigMode()))
    logger.debug('All RDF files found in Gitepo:' + str(config.getgraphsfromdir()))

    return {'config': config}


class FeaturesAction(argparse.Action):
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


def parseArgs(args):
    """Parse command line arguments."""
    basepathhelp = "Base path (aka. application root) (WSGI only)."
    graphhelp = """This option tells QuitStore how to map graph files and named graph URIs:
                "localconfig" - Use the given local file for graph settings.
                "repoconfig" - Use the configuration of the git repository for graphs settings.
                "graphfiles" - Use *.graph-files for each RDF file to get the named graph URI."""
    featurehelp = """This option enables additional features of the QuitStore:
                "provenance" - Store provenance information for each revision.
                "persistance" - Store all internal data as rdf graph."""
    confighelp = """Path of config file (turtle). Defaults to ./config.ttl."""
    loghelp = """Path to the log file."""
    targethelp = 'The directory of the local store repository.'

    port_default = 5000
    logfile_default = None
    basepath_default = None
    targetdir_default = None
    configfile_default = "config.ttl"
    oauthclientid_default = None
    oauthclientsecret_default = None

    if 'QUIT_PORT' in os.environ:
        port_default = os.environ['QUIT_PORT']

    if 'QUIT_LOGFILE' in os.environ:
        logfile_default = os.environ['QUIT_LOGFILE']

    if 'QUIT_BASEPATH' in os.environ:
        basepath_default = os.environ['QUIT_BASEPATH']

    if 'QUIT_TARGETDIR' in os.environ:
        targetdir_default = os.environ['QUIT_TARGETDIR']

    if 'QUIT_CONFIGFILE' in os.environ:
        configfile_default = os.environ['QUIT_CONFIGFILE']

    if 'QUIT_OAUTH_CLIENT_ID' in os.environ:
        oauthclientid_default = os.environ['QUIT_OAUTH_CLIENT_ID']

    if 'QUIT_OAUTH_SECRET' in os.environ:
        oauthclientsecret_default = os.environ['QUIT_OAUTH_SECRET']

    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--basepath', type=str, default=basepath_default, help=basepathhelp)
    parser.add_argument('-gc', '--garbagecollection', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-vv', '--verboseverbose', action='store_true')
    parser.add_argument('-c', '--configfile', type=str, default=configfile_default, help=confighelp)
    parser.add_argument('-l', '--logfile', type=str, default=logfile_default, help=loghelp)
    parser.add_argument('-r', '--repourl', type=str, help='A link/URI to a remote repository.')
    parser.add_argument('-t', '--targetdir', type=str, default=targetdir_default, help=targethelp)
    parser.add_argument('-cm', '--configmode', type=str, choices=[
        'graphfiles',
        'localconfig',
        'repoconfig'
    ], help=graphhelp)
    parser.add_argument('-f', '--features', nargs='*', action=FeaturesAction,
                        default=Feature.Unknown,
                        help=featurehelp)
    parser.add_argument('-p', '--port', default=port_default, type=int)
    parser.add_argument('--host', default='0.0.0.0', type=str)
    parser.add_argument('--oauth-clientid', default=oauthclientid_default, type=str)
    parser.add_argument('--oauth-clientsecret', default=oauthclientsecret_default, type=str)

    logger.debug("Parsing args: {}".format(args))

    return parser.parse_args(args)


def main(config, args):
    """Start the app."""
    app = create_app(config)
    app.run(debug=True, use_reloader=False, host=args.host, port=args.port)
