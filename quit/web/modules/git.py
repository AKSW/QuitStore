import sys
import traceback
import re
import pygit2

from flask import Blueprint, flash, redirect, request, url_for, current_app
from quit.web.app import render_template
from quit.web.extras.commits_graph import CommitGraph, generate_graph_data

__all__ = ['git']

git = Blueprint('git', __name__)


@git.route("/commits", defaults={'branch_or_ref': None}, methods=['GET'])
@git.route("/commits/<path:branch_or_ref>", methods=['GET'])
def commits(branch_or_ref):
    """
    Lists all commits of a given git branch.

    Returns:
        HTTP Response with commits.
    """
    quit = current_app.config['quit']
    default_branch = quit.config.getDefaultBranch()

    if not branch_or_ref and not quit.repository.is_empty:
        branch_or_ref = default_branch

    try:
        results = quit.repository.revisions(
            branch_or_ref, order=pygit2.GIT_SORT_TIME) if branch_or_ref else []
        data = generate_graph_data(CommitGraph.gets(results))

        return render_template('commits.html', results=results, data=data)

        if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
            results = res.serialize(format='html')
            response = make_response(render_template(
                "results.html", results=Markup(results.decode())))
            response.headers['Content-Type'] = 'text/html'
            return response
        elif mimetype in ['application/json', 'application/sparql-results+json']:
            response = make_response(res.serialize(format='json'), 200)
            response.headers['Content-Type'] = 'application/json'
            return response
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403


@git.route("/pull", methods=['POST', 'GET'])
def pull():
    """Pull from remote.

    Returns:
        HTTP Response 201: If pull was possible
        HTTP Response: 403: If pull did not work
    """
    try:
        current_app.config['quit'].repository.pull()
        return '', 201
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403


@git.route("/push", methods=['POST', 'GET'])
def push():
    """Pull from remote.

    Returns:
        HTTP Response 201: If push was possible
        HTTP Response: 403: If push did not work
    """
    try:
        current_app.config['quit'].repository.push()
        return '', 201
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403
