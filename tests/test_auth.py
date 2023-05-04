# SPDX-License-Identifier: GPL-2.0+

from base64 import b64encode
import pytest
import gssapi  # noqa
import mock
import json
from werkzeug.exceptions import Unauthorized
import waiverdb.auth
import flask_oidc
from flask import g


@pytest.fixture
def oidc_token(app):
    with mock.patch.object(flask_oidc.OpenIDConnect, '_get_token_info') as mocked:
        mocked.return_value = {
            'active': True, 'username': 'testuser', 'scope': 'openid waiverdb_scope'}
        with app.app_context():
            g.oidc_id_token = mocked()
            yield g.oidc_id_token


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
    waiver_data = {
        'subject': {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'},
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }

    def test_unauthorized(self, client, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        r = client.post('/api/v1.0/waivers/', content_type='application/json')
        assert r.status_code == 401
        assert r.headers.get('www-authenticate') == 'Negotiate'

    @mock.patch.multiple("gssapi.SecurityContext", complete=True,
                         __init__=mock.Mock(return_value=None),
                         step=mock.Mock(return_value=b"STOKEN"),
                         initiator_name="foo@EXAMPLE.ORG")
    @mock.patch.multiple("gssapi.Credentials",
                         __init__=mock.Mock(return_value=None),
                         __new__=mock.Mock(return_value=None))
    def test_authorized(self, client, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        headers = {'Authorization':
                   'Negotiate %s' % b64encode(b"CTOKEN").decode()}
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.waiver_data),
                        content_type='application/json', headers=headers)
        assert r.status_code == 201
        assert r.headers.get('WWW-Authenticate') == \
            'negotiate %s' % b64encode(b"STOKEN").decode()
        res_data = json.loads(r.data.decode('utf-8'))
        assert res_data['username'] == 'foo'

    def test_invalid_token(self, client, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        headers = {'Authorization': 'Negotiate INVALID'}
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.waiver_data),
                        content_type='application/json', headers=headers)
        assert r.status_code == 401
        assert r.json == {"message": "Invalid authentication token"}


class TestOIDCAuthentication(object):
    invalid_token_error = "Token required but invalid"
    auth_missing_error = "No 'Authorization' header found"

    def test_get_user_without_token(self, session):
        with pytest.raises(Unauthorized) as excinfo:
            request = mock.MagicMock()
            waiverdb.auth.get_user(request)
        assert self.auth_missing_error in str(excinfo.value)

    def test_get_user_with_invalid_token(self, oidc_token, session):
        oidc_token["active"] = False
        headers = {'Authorization': 'Bearer invalid'}
        request = mock.MagicMock()
        request.headers.return_value = mock.MagicMock(spec_set=dict)
        request.headers.__getitem__.side_effect = headers.__getitem__
        request.headers.__setitem__.side_effect = headers.__setitem__
        request.headers.__contains__.side_effect = headers.__contains__
        with pytest.raises(Unauthorized) as excinfo:
            waiverdb.auth.get_user(request)
        assert self.invalid_token_error in excinfo.value.get_description()

    def test_get_user_good(self, oidc_token, session):
        headers = {'Authorization': 'Bearer foobar'}
        request = mock.MagicMock()
        request.headers.return_value = mock.MagicMock(spec_set=dict)
        request.headers.__getitem__.side_effect = headers.__getitem__
        request.headers.__setitem__.side_effect = headers.__setitem__
        request.headers.__contains__.side_effect = headers.__contains__
        user, header = waiverdb.auth.get_user(request)
        assert user == oidc_token["username"]

    def test_warning_banner(
        self,
        verify_authorization,
        permissions,
        oidc_token,
        session,
        client,
    ):
        verify_authorization.side_effect = Unauthorized("Unauthorized")
        permissions.return_value = [{"testcases": ["a.b.c"], "groups": []}]
        headers = {'Authorization': 'Bearer foobar'}
        r = client.get('/api/v1.0/waivers/new?testcase=a.b.c', headers=headers)
        warning_banner = (
            '<div class="alert alert-danger" role="alert">'
            '401 Unauthorized: Unauthorized<br>'
            '<a href=/api/v1.0/permissions?testcase=a.b.c>'
            'See who has permission to waive a.b.c test case.</a></div>'
        )
        assert warning_banner in r.text
        assert r.status_code == 200

    def test_no_warning_banner(
        self,
        verify_authorization,
        permissions,
        oidc_token,
        session,
        client,
    ):
        verify_authorization.return_value = True
        permissions.return_value = [{"testcases": ["a.b.c"], "groups": []}]
        headers = {'Authorization': 'Bearer foobar'}
        r = client.get('/api/v1.0/waivers/new?testcase=a.b.c', headers=headers)
        assert "alert" not in r.text
        assert r.status_code == 200


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
        r = client.post('/api/v1.0/waivers/', content_type='application/json')
        assert r.status_code == 401


@pytest.mark.usefixtures('enable_kerberos_oidc_fallback')
class TestOIDCWithFallbackAuthentication(TestOIDCAuthentication):
    invalid_token_error = ""
    auth_missing_error = ""
