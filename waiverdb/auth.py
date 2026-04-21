# SPDX-License-Identifier: GPL-2.0+


import base64
import binascii
import json
import gssapi
from authlib.oauth2.base import OAuth2Error
from flask import current_app, Request, Response, session
from werkzeug.exceptions import Unauthorized

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
            raise Unauthorized("Attempted multiple GSSAPI round trips")

        current_app.logger.debug('Completed GSSAPI negotiation')

        stage = "getting remote user"
        user = str(sc.initiator_name)
        return user, token
    except gssapi.exceptions.GSSError as e:
        current_app.logger.exception(
            'Unable to authenticate: failed to %s: %s' %
            (stage, e.gen_message()))
        raise Unauthorized("Authentication failed")


def get_user(request: Request) -> tuple[str, dict[str, str]]:
    methods = auth_methods(current_app)

    # If there is an active OIDC session, use it directly without
    # trying other auth methods (e.g. Kerberos) that would fail.
    if "OIDC" in methods and session.get("oidc_auth_token"):
        return get_user_by_method(request, "OIDC")

    response = None
    error = ""

    for method in methods:
        try:
            return get_user_by_method(request, method)
        except Unauthorized as e:
            message = f"Authentication method {method} failed: {e}"
            current_app.logger.info(message)
            error += f"\n- {message}"
            if response is None and e.response is not None:
                response = e

    if response is not None:
        raise response

    if error:
        raise Unauthorized(f"Authentication failed:{error}")

    raise Unauthorized("Authenticated user required. No methods specified.")


def _oidc_session_sources():
    """Yield OIDC claim sources from the session: profile, decoded ID token,
    then decoded access token."""
    profile = session.get("oidc_auth_profile", {})
    if profile:
        yield profile

    token = session.get("oidc_auth_token", {})
    if isinstance(token, dict):
        if token.get("userinfo"):
            yield token["userinfo"]

        access_token = token.get("access_token", "")
        if access_token:
            # Token was already verified during OIDC login; just read claims.
            payload = access_token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            yield json.loads(base64.urlsafe_b64decode(payload))


def get_oidc_userinfo(field: str) -> str:
    for fields in _oidc_session_sources():
        if field in fields:
            return fields[field]

    try:
        fields = current_app.oidc.accept_token.acquire_token()
    except OAuth2Error as e:
        raise Unauthorized(f"OIDC authentication failed: {e}")

    if field not in fields:
        current_app.logger.error(
            "User info field %r is unavailable; available are: %s", field, fields.keys()
        )
        raise Unauthorized("Failed to retrieve username")

    return fields[field]


def get_oidc_groups() -> list[str] | None:
    groups_field = current_app.config.get('OIDC_GROUPS_FIELD')
    if not groups_field:
        return None

    def _sources():
        yield from _oidc_session_sources()
        try:
            yield current_app.oidc.accept_token.acquire_token()
        except OAuth2Error as e:
            current_app.logger.warning("Failed to acquire OIDC token: %s", e)

    for fields in _sources():
        value = fields
        for key in groups_field.split('.'):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
            if value is None:
                break

        if isinstance(value, list):
            return value

    current_app.logger.warning(
        "OIDC groups claim %r not found in any OIDC source", groups_field
    )
    return None


def get_user_by_method(request: Request, auth_method: str) -> tuple[str, dict[str, str]]:
    user = None
    headers = dict()
    if auth_method == 'OIDC':
        user = get_oidc_userinfo(current_app.config['OIDC_USERNAME_FIELD'])
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
