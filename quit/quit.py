#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')))

import argparse
from quit.core import GitRepo
from quit.conf import Feature, QuitConfiguration
from quit.exceptions import InvalidConfigurationError
from quit.utils import handle_exit
from quit.web.app import create_app
import logging
import subprocess

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

    if args.disableversioning:
        logger.info('Versioning: disabled')
        v = False
    else:
        logger.info('Versioning: enabled')
        v = True

    try:
        config = QuitConfiguration(
            versioning=v,
            configfile=args.configfile,
            targetdir=args.targetdir,
            repository=args.repourl,
            configmode=args.configmode,
            features=args.features,
        )
    except InvalidConfigurationError as e:
        logger.error(e)
        sys.exit('Exiting quit')

    if args.garbagecollection:
        try:
            with subprocess.Popen(
                ["git", "config", "gc.auto"],
                stdout=subprocess.PIPE,
                cwd=config.getRepoPath()
            ) as gcAutoThresholdProcess:
                stdout, stderr = gcAutoThresholdProcess.communicate()
                gcAutoThreshold = stdout.decode("UTF-8").strip()

            if not gcAutoThreshold:
                gcAutoThreshold = 256
                subprocess.Popen(
                    ["git", "config", "gc.auto", str(gcAutoThreshold)],
                    cwd=config.getRepoPath()
                )
                logger.info("Set default gc.auto threshold {}".format(gcAutoThreshold))

            logger.info(
                "Garbage Collection is enabled with gc.auto threshold {}".format(
                    gcAutoThreshold
                )
            )
        except Exception as e:
            # Disable garbage collection for the rest of the run because it
            # is likely that git is not available
            logger.info('Git garbage collection could not be configured and was disabled')
            logger.debug(e)

    # since repo is handled, we can add graphs to config
    config.initgraphconfig()

    logger.info('QuitStore successfully running.')
    logger.info('Known graphs: ' + str(config.getgraphs()))
    logger.info('Known files: ' + str(config.getfiles()))
    logger.debug('Path of Gitrepo: ' + config.getRepoPath())
    logger.debug('Config mode: ' + str(config.getConfigMode()))
    logger.debug('All RDF files found in Gitepo:' + str(config.getgraphsfromdir()))

    return {'config': config}


def savedexit():
    """Perform actions to be exevuted on API shutdown.

    Add methods you want to call on unexpected shutdown.
    """
    logger.info("Exiting store")


class FeaturesAction(argparse.Action):
    CHOICES = {'provenance': Feature.Provenance, 'persistence': Feature.Persistence}

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

    parser = argparse.ArgumentParser()
    parser.add_argument('-nv', '--disableversioning', action='store_true')
    parser.add_argument('-gc', '--garbagecollection', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-vv', '--verboseverbose', action='store_true')
    parser.add_argument('-c', '--configfile', type=str, default='config.ttl', help=confighelp)
    parser.add_argument('-l', '--logfile', type=str, help=loghelp)
    parser.add_argument('-r', '--repourl', type=str, help='A link/URI to a remote repository.')
    parser.add_argument('-t', '--targetdir', type=str, help=targethelp)
    parser.add_argument('-cm', '--configmode', type=str, choices=[
        'graphfiles',
        'localconfig',
        'repoconfig'
    ], help=graphhelp)
    parser.add_argument('-f', '--features', nargs='*', action=FeaturesAction, default=Feature.Unknown,
                        help=featurehelp)
    parser.add_argument('-p', '--port', default=5000, type=int)
    parser.add_argument('--host', default='0.0.0.0', type=str)

    return parser.parse_args(args)


def main(config):
    """Start the app."""
    app = create_app(config, enable_profiler=True)
    app.run(debug=True, use_reloader=False, host=args.host, port=args.port)


if __name__ == '__main__':
    args = parseArgs(sys.argv[1:])
    objects = initialize(args)

    config = objects['config']
    sys.setrecursionlimit(2 ** 15)

    # The app is started with an exit handler
    with handle_exit(savedexit):
        main(config)
