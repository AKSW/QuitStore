import traceback
import pygit2

from flask import Blueprint, request, current_app, make_response
from werkzeug.http import parse_accept_header
from quit.web.app import render_template
from quit.web.extras.commits_graph import CommitGraph, generate_graph_data
from quit.exceptions import QuitMergeConflict
from quit.utils import git_timestamp
from quit.web.modules.application import isLoggedIn, githubEnabled
import json
import logging
import re

logger = logging.getLogger('quit.web.modules.git')
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

    if not branch_or_ref:
        branch_or_ref = quit.getDefaultBranch()

    try:
        current_app.logger.debug(branch_or_ref)
        if not quit.repository.is_empty:
            results = quit.repository.revisions(branch_or_ref, order=pygit2.GIT_SORT_TIME)
        else:
            results = []

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


@git.route("/merge", defaults={'refspec': None}, methods=['GET', 'POST'])
@git.route("/merge/<path:refspec>", methods=['GET', 'POST'])
def merge(refspec):
    """Merge branch into target (refspec=<branch>:<target>).

    Merge 'branch' into 'target' and set 'target' to the resulting commit.

    Returns:
    HTTP Response 200: If merge was possible
    HTTP Response 201: If merge was possible and a merge commit was created
    HTTP Response 202: If merge was possible and a fast-forward happened
    HTTP Response 400: If merge did not work
    HTTP Response 409: If merge produces a conflict
    """
    quit = current_app.config['quit']

    try:
        if 'Accept' in request.headers:
            mimetype = parse_accept_header(request.headers['Accept']).best
        else:
            mimetype = '*/*'

        if mimetype in ['text/html', 'application/xhtml_xml']:
            response = make_response(render_template('merge.html'))
            response.headers['Content-Type'] = 'text/html'
            return response
        elif mimetype in ['application/json', '*/*']:
            # Actual Merge
            if refspec is None:
                refspec = request.values.get('refspec', None)

            if refspec:
                try:
                    branch, target = refspec.split(":")
                except ValueError:
                    branch = refspec
                    target = None
            else:
                branch = request.values.get('branch', None)
                target = request.values.get('target', None)
            method = request.values.get('method', None)
            try:
                result = quit.repository.merge(target=target, branch=branch, method=method)
            except QuitMergeConflict as mergeconflict:
                response = make_response(json.dumps(mergeconflict.getObject()), 409)
                response.headers['Content-Type'] = 'application/json'
                return response

            resultMessage = ""
            resultCode = 200

            if (result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD and result &
                    pygit2.GIT_MERGE_ANALYSIS_UNBORN):
                resultMessage = "{target} was unborn and is now set to {branch}".format(
                    target=target, branch=branch)
                resultCode = 202
            elif result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
                resultMessage = "{target} could be fast-forwarded to {branch}".format(
                    target=target, branch=branch)
                resultCode = 202
            elif result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
                resultMessage = "{target} is already up-to-date with {branch}".format(
                    target=target, branch=branch)
                resultCode = 200
            elif result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
                resultMessage = "{branch} was merged into {target}, merge commit created".format(
                    target=target, branch=branch)
                resultCode = 201
            else:
                resultMessage = "don't know what happened to {target} and {branch}".format(
                    target=target, branch=branch)

            result_object = {"status": result, "result_message": resultMessage}

            quit.syncAll()
            response = make_response(json.dumps(result_object), resultCode)
            response.headers['Content-Type'] = 'application/json'
            return response
        else:
            return "<pre>Unsupported Mimetype: {}</pre>".format(mimetype), 406

    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 400


@git.route("/branch", defaults={'refspec': None}, methods=['GET', 'POST'])
@git.route("/branch/<path:refspec>", methods=['GET', 'POST'])
def branch(refspec):
    """Branch two commits and set the result to branch_or_ref.

    merge branch into target and set branch_or_ref to the resulting commit
    - if only branch_or_ref is given, do nothing
    - if branch_or_ref and branch is given, merge branch into branch_or_ref and set branch_or_ref to
        the resulting commit
    - if branch_or_ref, branch and target are given, merge branch into target and set branch_or_ref
        to the resulting commit

    Returns:
    HTTP Response 200: If requesting the HTML interface
    HTTP Response 201: If branch was possible
    HTTP Response 400: If branching did not work or unsupported mimetype
    """
    quit = current_app.config['quit']

    try:
        if 'Accept' in request.headers:
            mimetype = parse_accept_header(request.headers['Accept']).best
        else:
            mimetype = '*/*'

        status = 200

        if refspec:
            oldbranch, newbranch = refspec.split(":")
            quit.repository.branch(oldbranch, newbranch)
        else:
            oldbranch = request.values.get('oldbranch')
            newbranch = request.values.get('newbranch')
            if newbranch:
                quit.repository.branch(oldbranch, newbranch)
                quit.syncAll()
                status = 201

        if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
            response = make_response(render_template('branch.html'))
            response.headers['Content-Type'] = 'text/html'
            return response, status
        else:
            return "<pre>Unsupported Mimetype: {}</pre>".format(mimetype), 400

    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 400


@git.route("/delete/branch", defaults={'refspec': None}, methods=['GET', 'POST'])
@git.route("/delete/branch/<path:refspec>", methods=['GET', 'POST'])
def del_branch(refspec):
    """Branch two commits and set the result to branch_or_ref.

    merge branch into target and set branch_or_ref to the resulting commit
    - if only branch_or_ref is given, do nothing
    - if branch_or_ref and branch is given, merge branch into branch_or_ref and set branch_or_ref to
        the resulting commit
    - if branch_or_ref, branch and target are given, merge branch into target and set branch_or_ref
        to the resulting commit

    Returns:
    HTTP Response 200: If requesting the HTML interface
    HTTP Response 201: If branch was possible
    HTTP Response 400: If branching did not work or unsupported mimetype
    """
    quit = current_app.config['quit']

    try:
        if 'Accept' in request.headers:
            mimetype = parse_accept_header(request.headers['Accept']).best
        else:
            mimetype = '*/*'

        refspec = re.sub("^refs/heads/", "", refspec)

        branch = quit.repository._repository.branches.get(refspec)
        if branch:
            branch.delete()
            message = "{} deleted".format(refspec)
            status = 200
        else:
            message = "{} not found".format(refspec)
            status = 404

        if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
            response = make_response(render_template('message.html', message=message))
            response.headers['Content-Type'] = 'text/html'
            return response, status
        else:
            return "<pre>Unsupported Mimetype: {}</pre>".format(mimetype), 400

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
