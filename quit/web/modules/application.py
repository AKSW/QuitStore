from flask import Blueprint
from flask import session, request, current_app, url_for
import logging
import urllib
import uuid
import json

logger = logging.getLogger('quit.modules.application')

application = Blueprint('application', __name__)


@application.route("/login", methods=['GET', 'POST'])
def login():
    if "state" not in session:
        state = str(uuid.uuid4())
        session["state"] = state
    else:
        state = session["state"]
    logger.debug("request url: {}".format(request.url))
    redirect_uri = 'http://docker.local/quitstore/login'
    authorizeEndpoint = "https://github.com/login/oauth/authorize"
    tokenEndpoint = "https://github.com/login/oauth/access_token"

    error = request.values.get('error', None)
    code = request.values.get('code', None)

    config = current_app.config['quit'].config

    if error or code is None:
        params = {'client_id': config.oauthclientid,
                  'redirect_uri': redirect_uri,
                  'scope': 'repo',
                  'state': state}
        loginURL = authorizeEndpoint + "?" + urllib.parse.urlencode(params)
        return "<a href='{}'>Login with GitHub</a>".format(loginURL)
    else:
        request_state = request.values.get('state', None)
        if not state == request_state:
            return "Error"
        post_data = {'client_id': config.oauthclientid,
                     'client_secret': config.oauthclientsecret,
                     'code': code,
                     'state': state}
        tokenrequest = urllib.request.Request(tokenEndpoint,
                                              urllib.parse.urlencode(post_data).encode())
        tokenrequest.add_header('Accept', 'application/json')
        tokenresponse = urllib.request.urlopen(tokenrequest).read().decode("utf-8")
        token = json.loads(tokenresponse)["access_token"]
        session["OAUTH_TOKEN"] = token
        return "success (<a href='{}'>back to quit</a>)".format(url_for("git.commits"))


@application.route("/logout", methods=['GET', 'POST'])
def logout():
    print(session)
    print("logout")
    session.clear()
    print("logout")
    print(session)
    return "you are successfully logged out (<a href='{}'>back to quit</a>)".format(
           url_for("git.commits"))


def isLoggedIn():
    """Returns true if OAUTH_TOKEN is set in the session."""
    if "OAUTH_TOKEN" in session:
        return True
    return False


def githubEnabled():
    """Returns true if oauthclientid and oauthclientsecret are configured."""
    config = current_app.config['quit'].config

    if config.oauthclientid and config.oauthclientsecret:
        return True
    return False
