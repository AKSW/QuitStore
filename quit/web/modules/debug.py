import sys
import traceback

from werkzeug.http import parse_accept_header
from flask import Blueprint, flash, redirect, request, url_for, current_app, make_response, Markup
from quit.conf import Feature
from quit.web.app import render_template, feature_required

__all__ = ('debug')

debug = Blueprint('debug', __name__)


@debug.route("/blame", defaults={'branch_or_ref': None}, methods=['GET'])
@debug.route("/blame/<branch_or_ref>", methods=['GET'])
@feature_required(Feature.Provenance)
def blame(branch_or_ref):

    quit = current_app.config['quit']
    default_branch = quit.config.getDefaultBranch() or 'master'

    if not branch_or_ref and not quit.repository.is_empty:
        branch_or_ref = default_branch

    blame = current_app.config['blame']

    if 'Accept' in request.headers:
        mimetype = parse_accept_header(request.headers['Accept']).best
    else:
        mimetype = 'application/sparql-results+json'

    try:
        res = blame.run(branch_or_ref=branch_or_ref)

        if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
            results = [{'commit': quit.repository.revision(
                row['hex']), 'blame': row} for row in res]
            response = make_response(render_template("blame.html", results=results))
            response.headers['Content-Type'] = 'text/html'
            return response
        elif mimetype in ['application/json', 'application/sparql-results+json']:
            response = make_response(res.serialize(format='json'), 200)
            response.headers['Content-Type'] = 'application/json'
            return response
        elif mimetype in [
            'application/rdf+xml', 'application/xml', 'application/sparql-results+xml'
        ]:
            response = make_response(res.serialize(format='xml'), 200)
            response.headers['Content-Type'] = 'application/rdf+xml'
            return response
        elif mimetype in ['application/csv', 'text/csv']:
            response = make_response(res.serialize(format='csv'), 200)
            response.headers['Content-Type'] = 'text/csv'
            return response
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.error(traceback.format_exc())
        return "<pre>" + traceback.format_exc() + "</pre>", 400
