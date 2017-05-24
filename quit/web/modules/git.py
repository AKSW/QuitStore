import re

from flask import Blueprint, flash, redirect, request, url_for, current_app
from quit.web.app import render_template

import sys, traceback

__all__ = [ 'git' ]

git = Blueprint('git', __name__)

@git.route("/pull", methods=['POST', 'GET'])
def pull():
    """Pull from remote.

    Returns:
        HTTP Response 201: If pull was possible
        HTTP Response: 403: If pull did not work
    """
    #if current_app.config['repository'].pull():
    #    return '', status.HTTP_201_CREATED
    #else:
    #    return '', status.HTTP_403_FORBIDDEN
    try:
        quit = current_app.config['quit']
        quit.repository.pull()
        return '', 201
    except Exception:
        return '', 403

@git.route("/push", methods=['POST', 'GET'])
def push():
    """Pull from remote.

    Returns:
        HTTP Response 201: If push was possible
        HTTP Response: 403: If push did not work
    """
    #if current_app.config['repository'].push():
    #    return '', status.HTTP_201_CREATED
    #else:
    #    return '', status.HTTP_403_FORBIDDEN

    try:
        quit = current_app.config['quit']
        quit.repository.push()
        return '', 201
    except Exception:
        return '', 403
