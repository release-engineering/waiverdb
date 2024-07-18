# SPDX-License-Identifier: GPL-2.0+


import base64
import binascii
import gssapi
import requests
from flask import current_app, Request, Response, session, g
from werkzeug.exceptions import Unauthorized, Forbidden

from waiverdb.utils import auth_methods

OIDC_AUTH_HEADER_PREFIX = "Bearer "


# Inspired by https://github.com/mkomitee/flask-kerberos/blob/master/flask_kerberos.py
# Later cleaned and ported to python-gssapi
def process_gssapi_request(token):
    try:
        stage = "initialize server context"
        sc = gssapi.SecurityContext(usage="accept")

        stage = "step context"
        token = sc.step(token if token != "" else None)  # nosec
        token = token if token is not None else ""

        # The current architecture cannot support continuation here
        stage = "checking completion"
        if not sc.complete:
            current_app.logger.error(
                'Multiple GSSAPI round trips not supported')
            raise Forbidden("Attempted multiple GSSAPI round trips")

        current_app.logger.debug('Completed GSSAPI negotiation')

        stage = "getting remote user"
        user = str(sc.initiator_name)
        return user, token
    except gssapi.exceptions.GSSError as e:
        current_app.logger.exception(
            'Unable to authenticate: failed to %s: %s' %
            (stage, e.gen_message()))
        raise Forbidden("Authentication failed")


def get_user(request: Request) -> tuple[str, dict[str, str]]:
    methods = auth_methods(current_app)

    exceptions = []

    for method in methods:
        try:
            return get_user_by_method(request, method)
        except Unauthorized as e:
            exceptions.append(e)
            continue

    if exceptions:
        raise exceptions[0]
    raise Unauthorized("Authenticated user required. No methods specified.")


def get_oidc_userinfo(field: str) -> str:
    fields = session.get("oidc_auth_profile", {})
    if field not in fields:
        current_app.logger.error(
            "User info field %r is unavailable; available are: %s", field, fields.keys()
        )
        raise Unauthorized("Failed to retrieve username")
    return fields[field]


def get_token_userinfo(request: Request, field: str) -> str:
    try:
        token_type, token_str = request.headers["Authorization"].split(None, maxsplit=1)
        if token_type != "Bearer":
            raise Unauthorized(f"Token type {token_type} is unsupported")
        introspection_ep = g._oidc_auth.load_server_metadata().get("introspection_endpoint")
        body = {
            'token': token_str,
            'client_id': current_app.config["OIDC_CLIENT_ID"],
            'client_secret': current_app.config["OIDC_CLIENT_SECRET"],
        }
        response = requests.post(
            introspection_ep, params=body,
            headers={'Content-type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        token = response.json()
        g.our_auth_token = token
    except Exception as e:
        raise Unauthorized(f"OIDC token authentication failed: {e}")
    try:
        if token.get("active"):
            return token[field]
        else:
            raise Unauthorized("active key not found in token")
    except AttributeError:
        raise Unauthorized(f"token has no keys (type is {type(token).__name__})")
    except KeyError:
        raise Unauthorized(f"field {field} not found in token")


def get_user_by_method(request: Request, auth_method: str) -> tuple[str, dict[str, str]]:
    user = None
    headers = dict()
    if auth_method == 'OIDC':
        try:
            user = get_oidc_userinfo(current_app.config['OIDC_USERNAME_FIELD'])
        except Unauthorized as u_exception:
            # fallback to check the token:
            if 'Authorization' in request.headers:
                user = get_token_userinfo(request, current_app.config['OIDC_USERNAME_FIELD'])
            else:
                raise u_exception
    elif auth_method == 'Kerberos':
        if 'Authorization' not in request.headers:
            response = Response('Unauthorized', 401, {'WWW-Authenticate': 'Negotiate'})
            raise Unauthorized(response=response)
        header = request.headers.get("Authorization")
        token = ''.join(header.strip().split()[1:])
        try:
            user, token = process_gssapi_request(base64.b64decode(token))
        except binascii.Error:
            raise Unauthorized("Invalid authentication token")
        # remove realm
        user = user.split("@")[0]
        headers = {'WWW-Authenticate': ' '.join(
            ['negotiate', base64.b64encode(token).decode()])}
    elif auth_method == 'SSL':
        # Nginx sets SSL_CLIENT_VERIFY and SSL_CLIENT_S_DN in request.environ
        # when doing SSL authentication.
        ssl_client_verify = request.environ.get('SSL_CLIENT_VERIFY')
        if ssl_client_verify != 'SUCCESS':
            raise Unauthorized('Cannot verify client: %s' % ssl_client_verify)
        if not request.environ.get('SSL_CLIENT_S_DN'):
            raise Unauthorized('Unable to get user information (DN) from the client certificate')
        user = request.environ.get('SSL_CLIENT_S_DN')
    elif auth_method == 'dummy':
        # Blindly accept any username. For testing purposes only of course!
        if not request.authorization:
            response = Response('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="dummy"'})
            raise Unauthorized(response=response)
        user = request.authorization.username
    else:
        raise Unauthorized(f"Unsupported authentication method {auth_method}")
    return user, headers
