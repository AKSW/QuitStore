import sys
import traceback
import re
import pygit2

from flask import Blueprint, flash, redirect, request, url_for, current_app, make_response
from werkzeug.http import parse_accept_header
from quit.web.app import render_template
from quit.web.extras.commits_graph import CommitGraph, generate_graph_data
from quit.utils import git_timestamp
import json

__all__ = ('git')

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

        if 'Accept' in request.headers:
            mimetype = parse_accept_header(request.headers['Accept']).best
        else:
            mimetype = '*/*'

        if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
            data = generate_graph_data(CommitGraph.gets(results))
            response = make_response(render_template('commits.html', results=results, data=data))
            response.headers['Content-Type'] = 'text/html'
            return response
        elif mimetype in ['application/json', 'application/sparql-results+json']:
            res = []
            for revision in results:
                res.append({"id": revision.id,
                            "author_name": revision.author.name,
                            "author_email": revision.author.email,
                            "author_time": str(git_timestamp(revision.author.time,
                                                             revision.author.offset)),
                            "committer_name": revision.committer.name,
                            "committer_email": revision.committer.email,
                            "committer_time": str(git_timestamp(revision.committer.time,
                                                                revision.committer.offset)),
                            "committer_offset": revision.committer.offset,
                            "message": revision.message,
                            "parrents": [parent.id for parent in revision.parents]})
            response = make_response(json.dumps(res), 200)
            response.headers['Content-Type'] = 'application/json'
            return response
        else:
            return "<pre>Unsupported Mimetype: {}</pre>".format(mimetype), 406
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403


@git.route("/pull", defaults={'remote': None}, methods=['POST', 'GET'])
@git.route("/pull/<path:remote>", methods=['GET', 'POST'])
def pull(remote):
    """Pull from remote.

    Returns:
        HTTP Response 201: If pull was possible
        HTTP Response: 403: If pull did not work
    """
    try:
        current_app.config['quit'].repository.pull(remote)
        return '', 201
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403


@git.route("/fetch", defaults={'remote': None}, methods=['POST', 'GET'])
@git.route("/fetch/<path:remote>", methods=['GET', 'POST'])
def fetch(remote):
    """Fetch from remote.

    Returns:
        HTTP Response 201: If pull was possible
        HTTP Response: 403: If pull did not work
    """
    try:
        current_app.config['quit'].repository.fetch(remote)
        return '', 201
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403


@git.route("/push", defaults={'remote': None}, methods=['POST', 'GET'])
@git.route("/push/<path:remote>", methods=['GET', 'POST'])
def push(remote):
    """Pull from remote.

    Returns:
        HTTP Response 201: If push was possible
        HTTP Response: 403: If push did not work
    """
    try:
        current_app.config['quit'].repository.push(remote)
        return '', 201
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403


@git.route("/merge", defaults={'branch_or_ref': None}, methods=['GET', 'POST'])
@git.route("/merge/<path:branch_or_ref>", methods=['GET', 'POST'])
def merge(branch_or_ref):
    """Merge two commits and set the result to branch_or_ref.

    merge branch into target and set branch_or_ref to the resulting commit
    - if only branch_or_ref is given, do nothing
    - if branch_or_ref and branch is given, merge branch into branch_or_ref and set branch_or_ref to
        the resulting commit
    - if branch_or_ref, branch and target are given, merge branch into target and set branch_or_ref
        to the resulting commit

    Returns:
        HTTP Response 201: If merge was possible
        HTTP Response: 403: If merge did fail
    """
    try:

        branch = request.values.get('branch', None) or None
        target = request.values.get('target', None) or branch_or_ref
        current_app.config['quit'].repository.merge(branch_or_ref, target, branch)
        return '', 201
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403


@git.route("/revert", defaults={'branch_or_ref': None}, methods=['GET', 'POST'])
@git.route("/revert/<path:branch_or_ref>", methods=['GET', 'POST'])
def revert(branch_or_ref):
    """Revert a commit.

    Returns:
        HTTP Response 201: If revert was possible
        HTTP Response: 403: If revert did fail
    """
    try:
        current_app.config['quit'].repository.revert()
        return '', 201
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403
