#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')))

import logging
from quit.application import getDefaults, parseEnv, parseArgs
from quit.web.app import create_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

logger = logging.getLogger('quit.run')

sys.setrecursionlimit(2 ** 15)

defaults = getDefaults()
env = parseEnv()
args = parseArgs(sys.argv[1:])
args = {**defaults, **env, **args}
application = create_app(args)

# Set the basepath
if args['basepath']:
    logger.info("Configure DispatcherMiddleware for basepath \"{}\"".format(args['basepath']))

    def simple(env, resp):
        """A simple WSGI application.

        See also: http://werkzeug.pocoo.org/docs/0.14/middlewares/
        """
        resp('200 OK', [('Content-Type', 'text/plain')])

    application.wsgi_app = DispatcherMiddleware(
            simple, {args['basepath']: application.wsgi_app})

def run():
    application.run(debug=args['flask_debug'],
                    use_reloader=False,
                    host=args['host'],
                    port=args['port'])

if __name__ == "__main__":
    run()
