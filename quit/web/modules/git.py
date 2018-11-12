import sys
import traceback
import re
import pygit2

from flask import Blueprint, flash, redirect, request, url_for, current_app, make_response
from werkzeug.http import parse_accept_header
from quit.web.app import render_template
from quit.web.extras.commits_graph import CommitGraph, generate_graph_data
from quit.utils import git_timestamp
from quit.web.modules.application import isLoggedIn, githubEnabled
import json

__all__ = ('git')

git = Blueprint('git', __name__)


@git.route("/commits", defaults={'branch_or_ref': None}, methods=['GET'])
@git.route("/commits/<path:branch_or_ref>", methods=['GET'])
def commits(branch_or_ref):
    """
    Lists all commits of a given git branch.

    Returns:
    HTTP Response 200: a list of commits
    HTTP Response 403: unknown branch or ref
    HTTP Response 406: Unsupported Mimetype requested
    """
    quit = current_app.config['quit']

    if not branch_or_ref and not quit.repository.is_empty:
        branch_or_ref = quit.getDefaultBranch()

    try:
        results = quit.repository.revisions(
            branch_or_ref, order=pygit2.GIT_SORT_TIME) if branch_or_ref else []

        if 'Accept' in request.headers:
            mimetype = parse_accept_header(request.headers['Accept']).best
        else:
            mimetype = '*/*'

        if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
            data = generate_graph_data(CommitGraph.gets(results))
            response = make_response(render_template('commits.html', results=results, data=data,
                                                     current_ref=branch_or_ref,
                                                     isLoggedIn=isLoggedIn,
                                                     githubEnabled=githubEnabled))
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


@git.route("/pull", defaults={'remote': None, "refspec": None}, methods=['POST', 'GET'])
@git.route("/pull/<remote>", defaults={"refspec": None}, methods=['GET', 'POST'])
@git.route("/pull/<remote>/<path:refspec>", methods=['GET', 'POST'])
def pull(remote, refspec):
    """Pull from remote.

    Arguments:
    remote -- The remote repository that is the source of the pull operation. The remote with
    its url has to be configured on the repository.
    refspec -- Specifies which refs to fetch and which local refs to update.

    Returns:
    HTTP Response 200: If pull was possible
    HTTP Response 201: If pull was possible and new commits were fetched or a merge commit was
                       created*
    HTTP Response 400: If pull did not work
    HTTP Response 409: If pull produces a conflict*
    (* not yet implemented)
    """
    if remote is None:
        remote = request.values.get('remote', None)
    if refspec is None:
        refspec = request.values.get('refspec', None)

    try:
        current_app.config['quit'].repository.pull(remote_name=remote, refspec=refspec)
        current_app.config['quit'].syncAll()
        return '', 200
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 400


@git.route("/fetch", defaults={'remote': None, "refspec": None}, methods=['POST', 'GET'])
@git.route("/fetch/<remote>", defaults={"refspec": None}, methods=['GET', 'POST'])
@git.route("/fetch/<remote>/<path:refspec>", methods=['GET', 'POST'])
def fetch(remote, refspec):
    """Fetch from remote.

    Arguments:
    remote -- The remote repository that is the source of the fetch operation. The remote with its
              url has to be configured on the repository.
    refspec -- Specifies which refs to fetch and which local refs to update.

    Returns:
    HTTP Response 200: If fetch was possible
    HTTP Response 201: If fetch was possible and new commits were fetched*
    HTTP Response 400: If fetch did not work
    HTTP Response 409: If fetch produces a conflict*
    (* not yet implemented)
    """
    if remote is None:
        remote = request.values.get('remote', None)
    if refspec is None:
        refspec = request.values.get('refspec', None)

    try:
        current_app.config['quit'].repository.fetch(remote, refspec)
        current_app.config['quit'].syncAll()
        return '', 200
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 400


@git.route("/push", defaults={'remote': None, "refspec": None}, methods=['POST', 'GET'])
@git.route("/push/<remote>", defaults={"refspec": None}, methods=['GET', 'POST'])
@git.route("/push/<remote>/<path:refspec>", methods=['GET', 'POST'])
def push(remote, refspec):
    """Push to remote.

    Arguments:
    remote -- The remote repository that is the destination of the push operation. The remote with
              its url has to be configured on the repository.
    refspec -- Specifies which refs to push and which remote refs to update.

    Returns:
    HTTP Response 200: If push was possible
    HTTP Response 400: If push did not work
    HTTP Response 409: If push produces a conflict on the remote end*
    (* not yet implemented)
    """
    if remote is None:
        remote = request.values.get('remote', None)
    if refspec is None:
        refspec = request.values.get('refspec', None)

    try:
        current_app.config['quit'].repository.push(remote, refspec)
        return '', 200
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 400


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
    HTTP Response 200: If merge was possible
    HTTP Response 201: If merge was possible and a merge commit was created*
    HTTP Response 400: If merge did not work
    HTTP Response 409: If merge produces a conflict*
    (* not yet implemented)
    """
    try:

        branch = request.values.get('branch', None) or None
        target = request.values.get('target', None) or branch_or_ref
        current_app.config['quit'].repository.merge(branch_or_ref, target, branch)
        current_app.config['quit'].syncAll()
        return '', 200
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 400


@git.route("/revert", defaults={'branch_or_ref': None}, methods=['GET', 'POST'])
@git.route("/revert/<path:branch_or_ref>", methods=['GET', 'POST'])
def revert(branch_or_ref):
    """Revert a commit.

    Returns:
    HTTP Response 201: If revert was possible and a revert commit was created
    HTTP Response 400: If revert did fail
    """
    try:
        current_app.config['quit'].repository.revert()
        current_app.config['quit'].syncAll()
        return '', 201
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 400
