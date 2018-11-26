#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')))

import logging
from quit.application import parseArgs, initialize
from quit.web.app import create_app
from werkzeug.wsgi import DispatcherMiddleware

logger = logging.getLogger('quit.run')

parsedArgs = parseArgs(sys.argv[1:])

if __name__ == "__main__":
    from flask_uwsgi_websocket._uwsgi import run_uwsgi

    run_uwsgi("quit.run:application", parsedArgs.flask_debug, parsedArgs.host, parsedArgs.port,
              pyargv="\"{}\"".format(" ".join(sys.argv[1:])))
else:
    objects = initialize(parsedArgs)
    config = objects['config']
    sys.setrecursionlimit(2 ** 15)
    application = create_app(config)

    # Set the basepath
    if parsedArgs.basepath:
        logger.info("Configure DispatcherMiddleware for basepath \"{}\"".format(
                    parsedArgs.basepath))

        def simple(env, resp):
            """A simple WSGI application.

            See also: http://werkzeug.pocoo.org/docs/0.14/middlewares/
            """
            resp('200 OK', [('Content-Type', 'text/plain')])

        application.wsgi_app = DispatcherMiddleware(simple,
                                                    {parsedArgs.basepath: application.wsgi_app})
