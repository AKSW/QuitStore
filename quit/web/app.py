import os

from flask import Flask, render_template as rt, g, current_app
from flask.ext.cors import CORS

from quit.conf import QuitConfiguration
from quit.core import MemoryStore, Quit
from quit.git import Repository

from quit.namespace import QUIT
from quit.service import register
from quit.provenance import Blame

# For import *
__all__ = ['create_app']

def create_app(config):
    """Create a Flask app."""

    app = Flask(__name__.split('.')[0], template_folder='web/templates', static_folder='web/static')
    register_app(app, config)
    register_hook(app)
    register_blueprints(app)
    register_extensions(app)
    register_logging(app)
    register_errorhandlers(app)
  
    return app


def register_app(app, config):
    """Different ways of configurations."""

    repository = Repository(config.getRepoPath(), create=True)
    
    quit = Quit(config, repository, MemoryStore())
    quit.sync()
    
    content = quit.store.store.serialize(format='trig').decode()
    for line in (content.splitlines()):
        print(line)

    app.config['quit'] = quit
    app.config['blame'] = Blame(quit)
    register(QUIT.service, quit.store)

def register_extensions(app):
    """Register extensions."""
    
    cors = CORS()
    cors.init_app(app)

def register_blueprints(app):
    """Register blueprints in views."""

    from quit.web.modules.debug import debug
    from quit.web.modules.endpoint import endpoint
    from quit.web.modules.git import git
        
    for bp in [debug, endpoint, git]:
        app.register_blueprint(bp)


def register_logging(app):
    """Register file(info) and email(error) logging."""

    if app.debug or app.testing:
        # Skip debug and test mode. Just check standard output.
        return

    import logging
    import os

    app.logger.setLevel(logging.DEBUG)
    
    # logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create file handler which logs even debug messages
    fh = logging.FileHandler('quit.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    ch.setFormatter(formatter)
    
    # add the handlers to the logger
    app.logger.addHandler(fh)
    app.logger.addHandler(ch)

def register_hook(app):
    import time

    @app.before_request
    def before_request():
        g.start=time.time()

    @app.after_request
    def after_request(response):
        diff = time.time() - g.start
        return response


def register_errorhandlers(app):

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

def render_template(template_name_or_list, **kwargs):

    quit = current_app.config['quit']

    context = {
        'available_branches': quit.repository.branches,
        'available_tags': quit.repository.tags, 
    }
    context.update(kwargs)

    return rt(template_name_or_list, **context)

