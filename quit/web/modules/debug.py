from flask import Blueprint, flash, redirect, request, url_for, current_app
from quit.web.app import render_template

from werkzeug.http import parse_accept_header
import sys, traceback

__all__ = [ 'debug' ]

debug = Blueprint('debug', __name__)

@debug.route("/blame", defaults={'branch_or_ref': 'master'}, methods=['GET'])
@debug.route("/blame/<branch_or_ref>", methods=['GET'])
def blame(branch_or_ref):

    if 'Accept' in request.headers:
        mimetype = parse_accept_header(request.headers['Accept']).best
    else:
        mimetype = 'text/html'

    try:
        if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
            results = current_app['blame'].run(branch_or_ref)
            return render_template('blame.html', results=results)
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>"+traceback.format_exc()+"</pre>", 400