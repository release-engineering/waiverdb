# SPDX-License-Identifier: GPL-2.0+

from base64 import b64encode
import pytest
import gssapi  # noqa
import mock
import json
from werkzeug.exceptions import Unauthorized
import waiverdb.auth
from flask import session, request

WAIVER_DATA = {
    'subject_type': 'koji_build',
    'subject_identifier': 'glibc-2.26-27.fc27',
    'testcase': 'testcase1',
    'product_version': 'fool-1',
    'waived': True,
    'comment': 'it broke',
}
WAIVER_PARAMS = '&'.join(
    f'{k}={v}'
    for k, v in WAIVER_DATA.items()
    if isinstance(v, str)
)


@pytest.fixture
def oidc_auth_profile(app):
    with app.test_request_context('/api/v1.0/waivers/new'):
        with mock.patch.dict(session, {'oidc_auth_profile': {
            'active': True,
            'username': 'testuser',
            'preferred_username': 'testuser_preferred',
            'scope': 'openid waiverdb_scope',
        }, 'oidc_auth_token': {}}) as mocked:
            yield mocked['oidc_auth_profile']


@pytest.fixture
def oidc_token(app):
    with app.test_request_context('/api/v1.0/waivers/new'):
        with mock.patch.dict(session, {'oidc_auth_token': {
            'active': True,
            'username': 'testuser',
            'preferred_username': 'testuser_preferred',
            'scope': 'openid waiverdb_scope',
        }, 'oidc_auth_profile': {}}) as mocked:
            yield mocked['oidc_auth_token']


@pytest.fixture
def verify_authorization():
    with mock.patch("waiverdb.api_v1.verify_authorization") as mocked:
        yield mocked


@pytest.fixture
def permissions():
    with mock.patch("waiverdb.api_v1.permissions") as mocked:
        yield mocked


@pytest.mark.usefixtures('enable_kerberos')
class TestGSSAPIAuthentication(object):
    def test_unauthorized(self, client, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        r = client.post('/api/v1.0/waivers/', data=json.dumps(WAIVER_DATA),
                        content_type='application/json')
        assert r.status_code == 401
        assert r.headers.get('www-authenticate') == 'Negotiate'

    @mock.patch.multiple("gssapi.SecurityContext", complete=True,
                         __init__=mock.Mock(return_value=None),
                         step=mock.Mock(return_value=b"STOKEN"),
                         initiator_name="foo@EXAMPLE.ORG")
    @mock.patch.multiple("gssapi.Credentials",
                         __init__=mock.Mock(return_value=None),
                         __new__=mock.Mock(return_value=None))
    def test_authorized(self, client, monkeypatch, session):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        headers = {'Authorization': f'Negotiate {b64encode(b"CTOKEN").decode()}'}
        r = client.post('/api/v1.0/waivers/', data=json.dumps(WAIVER_DATA),
                        content_type='application/json', headers=headers)
        assert r.status_code == 201
        assert r.headers.get('WWW-Authenticate') == f'negotiate {b64encode(b"STOKEN").decode()}'
        res_data = json.loads(r.data.decode('utf-8'))
        assert res_data['username'] == 'foo'

    def test_invalid_token(self, client, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        headers = {'Authorization': 'Negotiate INVALID'}
        r = client.post('/api/v1.0/waivers/', data=json.dumps(WAIVER_DATA),
                        content_type='application/json', headers=headers)
        assert r.status_code == 401
        assert r.json == {"message": "Invalid authentication token"}


class TestOIDCAuthentication(object):
    auth_missing_error = "401 Unauthorized: Failed to retrieve username"

    def test_get_user_no_auth_methods(self):
        with mock.patch('waiverdb.auth.auth_methods') as mocked:
            mocked.return_value = []
            with pytest.raises(Unauthorized) as excinfo:
                waiverdb.auth.get_user(request)
        assert "Authenticated user required. No methods specified." in str(excinfo.value)

    def test_get_user_without_profile(self, app):
        with app.test_request_context('/api/v1.0/waivers/new'):
            with pytest.raises(Unauthorized) as excinfo:
                waiverdb.auth.get_user(request)
        assert self.auth_missing_error in str(excinfo.value)

    def test_get_user_good_profile(self, oidc_auth_profile):
        user, header = waiverdb.auth.get_user(request)
        assert user == oidc_auth_profile["preferred_username"]

    def test_get_user_good_token(self, oidc_token):
        user, header = waiverdb.auth.get_user(request)
        assert user == oidc_token["username"]

    # tests only redirect of deprecated resource
    # not working, causing an exception in flask_oidc library:
    # https://github.com/fedora-infra/flask-oidc/issues/93
    """
    def test_create_new_waiver(
        self,
        verify_authorization,
        permissions,
        oidc_token,
        client,
    ):
        verify_authorization.return_value = True
        permissions.return_value = [{"testcases": ["a.b.c"], "groups": []}]
        headers = {'Authorization': 'Bearer foobar'}
        url = f'/api/v1.0/waivers/create?{WAIVER_PARAMS}'
        r = client.get(
            url,
            headers=headers,
            follow_redirects=True,
        )
        assert r.request.base_url.endswith('/api/v1.0/waivers/new')
        expected_args = {
            k: v
            for k, v in WAIVER_DATA.items()
            if isinstance(v, str)
        }
        assert dict(r.request.args) == expected_args
        assert 'new_waiver_id' not in dict(r.request.args)
    """


@pytest.mark.usefixtures('enable_ssl')
class TestSSLAuthentication(object):
    def test_SSL_CLIENT_VERIFY_is_not_set_should_raise_error(self):
        with pytest.raises(Unauthorized) as excinfo:
            request = mock.MagicMock()
            waiverdb.auth.get_user(request)
        assert 'Cannot verify client' in excinfo.value.get_description()

    def test_SSL_CLIENT_S_DN_is_not_set_should_raise_error(self):
        with pytest.raises(Unauthorized) as excinfo:
            request = mock.MagicMock(environ={'SSL_CLIENT_VERIFY': 'SUCCESS'})
            waiverdb.auth.get_user(request)
        assert 'Unable to get user information (DN) from the client certificate' \
               in excinfo.value.get_description()

    def test_good_ssl_cert(self):
        ssl = {
            'SSL_CLIENT_VERIFY': 'SUCCESS',
            'SSL_CLIENT_S_DN': 'testuser',
        }
        request = mock.MagicMock(environ=ssl)
        user, header = waiverdb.auth.get_user(request)
        assert user == 'testuser'


@pytest.mark.usefixtures('enable_kerberos_oidc_fallback')
class TestKerberosWithFallbackAuthentication(TestGSSAPIAuthentication):
    def test_unauthorized(self, client, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        r = client.post('/api/v1.0/waivers/', data=json.dumps(WAIVER_DATA),
                        content_type='application/json')
        assert r.status_code == 401


@pytest.mark.usefixtures('enable_kerberos_oidc_fallback')
class TestOIDCWithFallbackAuthentication(TestOIDCAuthentication):
    auth_missing_error = ""
