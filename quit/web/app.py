import sys
import os
import urllib
import hashlib
import rdflib
import logging

from functools import wraps

from flask import Flask, render_template as rt, render_template_string as rts, g, current_app
from flask import request, url_for, redirect, make_response
from flask.ext.cors import CORS

from jinja2 import Environment, contextfilter, Markup

from quit.conf import QuitConfiguration
from quit.core import MemoryStore, Quit
from quit.git import Repository

from quit.namespace import QUIT
from quit.web.service import register
from quit.provenance import Blame

logger = logging.getLogger('quit.web.app')

# For import *
__all__ = ['create_app']

DROPDOWN_TEMPLATE = """
<div class="dropdown branch-select">
    <button class="btn btn-default dropdown-toggle" type="button" data-toggle="dropdown">
        <i class="fa fa-code-fork" aria-hidden="true"></i> Branches <span class="caret"></span>
    </button>
    <ul class="dropdown-menu">
        <li class="dropdown-header">Branches</li>
        {% for branch in branches %}
            <li>
                <a href="{{ url_for(request.endpoint, branch_or_ref=branch) }}">{{ branch }}</a>
            </li>
        {% endfor %}
        {% if tags %}
            <li class="divider"></li>
            <li class="dropdown-header">Tags</li>
            {% for tag in tags %}
                <li><a href="{{ url_for(request.endpoint, branch_or_ref=tag) }}">{{ tag }}</a></li>
            {% endfor %}
        {% endif %}
    </ul>
</div>
"""

env = Environment()


def feature_required(feature):
    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_app.config['quit'].config.hasFeatures(feature):
                return render_template("config_error.html"), 404
            return f(*args, **kwargs)
        return decorated_view
    return wrapper


def create_app(config, enable_profiler=False, profiler_quiet=False):
    """Create a Flask app."""

    app = Flask(
        __name__.split('.')[0], template_folder='web/templates', static_folder='web/static'
    )
    register_app(app, config)
    register_hook(app)
    register_blueprints(app)
    register_extensions(app)
    register_errorhandlers(app)
    register_template_helpers(app)

    if enable_profiler:
        from werkzeug.contrib.profiler import ProfilerMiddleware, MergeStream

        f = open('profiler.log', 'w')

        if profiler_quiet:
            app.wsgi_app = ProfilerMiddleware(
                app.wsgi_app, f, profile_dir="c:/tmp")
        else:
            stream = MergeStream(sys.stdout, f)
            app.wsgi_app = ProfilerMiddleware(
                app.wsgi_app, stream, profile_dir="c:/tmp")

    return app


def register_app(app, config):
    """Different ways of configurations."""

    repository = Repository(config.getRepoPath(), create=True)
    bindings = config.getBindings()

    quit = Quit(config, repository, MemoryStore(bindings))
    quit.syncAll()

    content = quit.store.store.serialize(format='trig').decode()
    logger.debug("Initialize store with following content: {}".format(content))
    logger.debug("Initialize store with following graphs: {}".format(
        quit.config.getgraphurifilemap())
    )

    app.config['quit'] = quit
    app.config['blame'] = Blame(quit)
    register(QUIT.service, quit.store.store)


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

    @app.route("/")
    def index():
        return redirect(url_for('git.commits'))


def register_hook(app):
    import time

    @app.before_request
    def before_request():
        g.start = time.time()

    @app.after_request
    def after_request(response):
        diff = time.time() - g.start
        return response


def register_errorhandlers(app):

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

    from flask import request

    def shutdown_server():
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    @app.route('/shutdown', methods=['GET'])
    def shutdown():
        shutdown_server()
        return 'Server shutting down...'


def register_template_helpers(app):

    @app.template_filter('gravatar')
    def gravatar_lookup(email, size=36):
        gravatar_url = "https://www.gravatar.com/avatar/" + \
            hashlib.md5(email.lower().encode()).hexdigest() + "?"
        gravatar_url += urllib.parse.urlencode({'s': str(size)})
        return gravatar_url

    @contextfilter
    @app.template_filter('term_to_string')
    def term_to_string(ctx, t):
        def qname(ctx, t):
            try:
                config = ctx.get('config')
                link = config['quit'].store.store.compute_qname(t, False)
                return u'%s:%s' % (link[0], link[2])
            except Exception as e:
                return t

        if isinstance(t, rdflib.URIRef):
            link = qname(ctx, t)
            return Markup("<a href='%s'>%s</a>" % (t, link))
        elif isinstance(t, rdflib.Literal):
            if t.language:
                return '"%s"@%s' % (t, t.language)
            elif t.datatype:
                return '"%s"^^&lt;%s&gt;' % (t, qname(ctx, t.datatype))
            else:
                return '"%s"' % t
        return t

    @app.context_processor
    def context_processor():
        def render_dropdown(available_branches, available_tags):
            branches_prefix = 'refs/heads/'
            branches = [x[len(branches_prefix):] if x.startswith(
                branches_prefix) else x for x in available_branches]
            tags_prefix = 'refs/heads/'
            tags = [x[len(tags_prefix):] if x.startswith(
                tags_prefix) else x for x in available_tags]
            return rts(DROPDOWN_TEMPLATE, branches=branches, tags=tags)

        return dict(render_dropdown=render_dropdown)


def render_template(template_name_or_list, **kwargs):

    quit = current_app.config['quit']

    available_branches = quit.repository.branches
    available_tags = quit.repository.tags

    context = {
        'available_branches': available_branches,
        'available_tags': available_tags
    }
    context.update(kwargs)

    return rt(template_name_or_list, **context)
