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

logger = logging.getLogger('quit.web.modules.websocket')

websocket = Blueprint('websocket', __name__)

@websocket.route('/echo')
def echo(ws):
    while True:
        msg = ws.receive()
        ws.send(msg)

@websocket.route("/commits_updates", defaults={'branch_or_ref': None}, methods=['GET'])
@websocket.route("/commits_updates/<path:branch_or_ref>", methods=['GET'])
def commits(ws, branch_or_ref):
    """
    Lists all commits of a given git branch.

    Returns:
    HTTP Response 200: a list of commits
    HTTP Response 403: unknown branch or ref
    HTTP Response 406: Unsupported Mimetype requested
    """
    ws.send("Hallo you want to get commits, lets see …")
    print(ws)
    print(ws.environ)

    quit = current_app.config['quit']

    if not branch_or_ref:
        branch_or_ref = quit.getDefaultBranch()
    ws.send("Hallo you want to get commits on {}".format(branch_or_ref))

    try:
        current_app.logger.debug(branch_or_ref)
        if not quit.repository.is_empty:
            results = quit.repository.revisions(branch_or_ref, order=pygit2.GIT_SORT_TIME)
        else:
            results = []

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
        ws.send(json.dumps(res))
        print(ws)

        list = []

        def updateCallback(commitId):
            print("Update came in with commitId: {}".format(commitId))
            list.append(commitId)

        quit.subscribe(updateCallback)
        prev = 0
        while True:
            if len(list) > prev:
                ws.send(list)

    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 403
