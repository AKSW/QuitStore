import os
import urllib
import hashlib
import rdflib
import logging

from functools import wraps

from flask import Flask, render_template as rt, render_template_string as rts, g, current_app
from flask import url_for, redirect, session, request
from flask_cors import CORS

from jinja2 import Environment, contextfilter, Markup

from quit.conf import Feature as QuitFeature
from quit.core import MemoryStore, Quit
from quit.git import Repository, QuitRemoteCallbacks
import quit.utils as utils

from quit.namespace import QUIT
from quit.web.service import register
from quit.provenance import Blame

logger = logging.getLogger('quit.web.app')

# For import *
__all__ = ('create_app')

BRANCHES_DROPDOWN_TEMPLATE = """
<span class="dropdown branch-select">
    <button class="btn btn-default dropdown-toggle" type="button" data-toggle="dropdown">
        <i class="fa fa-code-fork" aria-hidden="true"></i> {{ current_ref }}
        <span class="caret"></span>
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
</span>
"""

REMOTES_DROPDOWN_TEMPLATE = """
<div class="form-group">
<label class="control-label" for="remote">
    <i class="fa fa-cloud" aria-hidden="true"></i> Remote:</span>
</label>
<select name="remote" class="form-control branch-select">
    {% for remote in remotes %}
        <option value="{{ remote.name }}"> {{ remote.name }}
        <small>({{ remote.url }})</small></option>
    {% endfor %}
</select>
</div>
"""

env = Environment()


def feature_required(feature):
    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_app.config['quit'].config.hasFeature(feature):
                return render_template("config_error.html"), 404
            return f(*args, **kwargs)
        return decorated_view
    return wrapper


def create_app(config):
    """Create a Flask app."""

    app = Flask(
        __name__.split('.')[0], template_folder='web/templates', static_folder='web/static'
    )
    app.secret_key = os.urandom(24)
    register_app(app, config)
    register_hook(app)
    register_blueprints(app, config)
    register_extensions(app)
    register_errorhandlers(app)
    register_template_helpers(app)

    return app


def register_app(app, config):
    """Different ways of configurations."""

    garbageCollection = config.hasFeature(QuitFeature.GarbageCollection)
    logger.debug("Has Garbage collection feature?: {}".format(garbageCollection))

    repository = Repository(config.getRepoPath(), create=True, garbageCollection=garbageCollection,
                            callback=QuitRemoteCallbacks(session=session))
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


def register_blueprints(app, config):
    """Register blueprints in views."""

    from quit.web.modules.debug import debug
    from quit.web.modules.endpoint import endpoint
    from quit.web.modules.git import git
    from quit.web.modules.application import application

    for bp in [debug, endpoint, git, application]:
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
        def render_branches_dropdown(current_ref, available_branches, available_tags):
            branches_prefix = 'refs/heads/'
            branches = [x[len(branches_prefix):] if x.startswith(
                branches_prefix) else x for x in available_branches]
            tags_prefix = 'refs/heads/'
            tags = [x[len(tags_prefix):] if x.startswith(
                tags_prefix) else x for x in available_tags]
            return rts(BRANCHES_DROPDOWN_TEMPLATE, current_ref=current_ref, branches=branches,
                       tags=tags)

        def render_remotes_dropdown(available_remotes):
            return rts(REMOTES_DROPDOWN_TEMPLATE, remotes=available_remotes)

        return dict(render_branches_dropdown=render_branches_dropdown,
                    render_remotes_dropdown=render_remotes_dropdown)


def render_template(template_name_or_list, **kwargs):

    quit = current_app.config['quit']

    current_head = quit.repository.current_head
    available_branches = quit.repository.branches
    available_tags = quit.repository.tags
    available_remotes = quit.repository.remotes
    available_refs = quit.repository.references

    context = {
        'current_ref': current_head,
        'available_refs': available_refs,
        'available_branches': available_branches,
        'available_tags': available_tags,
        'available_remotes': available_remotes,
        'git_timestamp': utils.git_timestamp
    }
    context.update(kwargs)

    return rt(template_name_or_list, **context)
