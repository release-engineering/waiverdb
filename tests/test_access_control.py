# SPDX-License-Identifier: GPL-2.0+

import json
from base64 import b64encode

import mock
import ldap
import pytest
from click.testing import CliRunner
from textwrap import dedent
from werkzeug.exceptions import Unauthorized
from waiverdb.cli import cli as waiverdb_cli


@pytest.mark.usefixtures('enable_permission_mapping')
@pytest.mark.usefixtures('enable_kerberos')
@mock.patch.multiple("gssapi.SecurityContext", complete=True,
                     __init__=mock.Mock(return_value=None),
                     step=mock.Mock(return_value=b"STOKEN"),
                     initiator_name="foo@EXAMPLE.ORG")
@mock.patch.multiple("gssapi.Credentials",
                     __init__=mock.Mock(return_value=None),
                     __new__=mock.Mock(return_value=None))
class TestAccessControl(object):

    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    headers = {'Authorization':
               'Negotiate %s' % b64encode(b"CTOKEN").decode()}

    def test_ldap_host_base_not_defined(self, client, session):
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.data),
                        content_type='application/json', headers=self.headers)
        res_data = json.loads(r.get_data(as_text=True))
        assert r.status_code == 500
        assert res_data['message'] == ("LDAP_HOST and LDAP_BASE also need to be "
                                       "defined if PERMISSION_MAPPING is defined.")

    @pytest.mark.usefixtures('enable_ldap_host')
    def test_ldap_host_defined_base_not(self, client, session):
        self.test_ldap_host_base_not_defined(client, session)

    @pytest.mark.usefixtures('enable_ldap_base')
    def test_ldap_base_defined_host_not(self, client, session):
        self.test_ldap_host_base_not_defined(client, session)

    @pytest.mark.usefixtures('enable_ldap_host')
    @pytest.mark.usefixtures('enable_ldap_base')
    @mock.patch('ldap.initialize', side_effect=ldap.LDAPError())
    def test_initialization_ldap_connection(self, mocked, client, session):
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.data),
                        content_type='application/json', headers=self.headers)
        res_data = json.loads(r.get_data(as_text=True))
        assert r.status_code == 401
        assert res_data['message'] == "Some error occured initializing the LDAP connection."

    @pytest.mark.usefixtures('enable_ldap_host')
    @pytest.mark.usefixtures('enable_ldap_base')
    @mock.patch('waiverdb.api_v1.WaiversResource.get_group_membership', return_value=([]))
    def test_user_not_found_in_ldap(self, mocked_conn, client, session, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.data),
                        content_type='application/json', headers=self.headers)
        res_data = json.loads(r.get_data(as_text=True))
        assert r.status_code == 401
        assert res_data['message'] == "Couldn't find user foo in LDAP"

    @pytest.mark.usefixtures('enable_ldap_host')
    @pytest.mark.usefixtures('enable_ldap_base')
    @mock.patch('waiverdb.api_v1.WaiversResource.get_group_membership',
                return_value=(['factory-2-0', 'something-else']))
    def test_group_has_permission(self, mocked_conn, client, session, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.data),
                        content_type='application/json', headers=self.headers)
        res_data = json.loads(r.get_data(as_text=True))
        assert r.status_code == 201
        assert res_data['username'] == 'foo'
        assert res_data['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
        assert res_data['subject_type'] == 'koji_build'
        assert res_data['subject_identifier'] == 'glibc-2.26-27.fc27'
        assert res_data['testcase'] == 'testcase1'
        assert res_data['product_version'] == 'fool-1'
        assert res_data['waived'] is True
        assert res_data['comment'] == 'it broke'

    @pytest.mark.usefixtures('enable_ldap_host')
    @pytest.mark.usefixtures('enable_ldap_base')
    def test_user_has_permission(self, client, session, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        self.data['testcase'] = 'testcase2'
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.data),
                        content_type='application/json', headers=self.headers)
        res_data = json.loads(r.get_data(as_text=True))
        assert r.status_code == 201
        assert res_data['username'] == 'foo'
        assert res_data['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
        assert res_data['subject_type'] == 'koji_build'
        assert res_data['subject_identifier'] == 'glibc-2.26-27.fc27'
        assert res_data['testcase'] == 'testcase2'
        assert res_data['product_version'] == 'fool-1'
        assert res_data['waived'] is True
        assert res_data['comment'] == 'it broke'

    @pytest.mark.usefixtures('enable_ldap_host')
    @pytest.mark.usefixtures('enable_ldap_base')
    @mock.patch('waiverdb.api_v1.WaiversResource.get_group_membership',
                return_value=(['factory-2-0', 'something-else']))
    def test_both_user_group_no_permission(self, mocked_conn, client, session, monkeypatch):
        monkeypatch.setenv('KRB5_KTNAME', '/etc/foo.keytab')
        self.data['testcase'] = 'testcase3'
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.data),
                        content_type='application/json', headers=self.headers)
        res_data = json.loads(r.get_data(as_text=True))
        assert r.status_code == 401
        assert res_data['message'] == ("You are not authorized to submit a waiver "
                                       "for the test case testcase3")

    @pytest.mark.usefixtures('enable_ldap_host')
    @pytest.mark.usefixtures('enable_ldap_base')
    @mock.patch('waiverdb.auth.get_user', return_value=('bodhi', {}))
    @mock.patch('waiverdb.api_v1.WaiversResource.get_group_membership',
                return_value=(['factory-2-0', 'something-else']))
    def test_proxied_by_with_no_permission(self, mocked_conn, mock_get_user, client, session):
        self.data['testcase'] = 'testcase3'
        self.data['username'] = 'foo'
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.data),
                        content_type='application/json', headers=self.headers)
        res_data = json.loads(r.get_data(as_text=True))
        assert r.status_code == 401
        assert res_data['message'] == ("You are not authorized to submit a waiver "
                                       "for the test case testcase3")

    @pytest.mark.usefixtures('enable_ldap_host')
    @pytest.mark.usefixtures('enable_ldap_base')
    @mock.patch('waiverdb.auth.get_user', return_value=('bodhi', {}))
    @mock.patch('waiverdb.api_v1.WaiversResource.get_group_membership',
                return_value=(['factory-2-0', 'something-else']))
    def test_proxied_by_has_permission(self, mocked_conn, mock_get_user, client, session):
        self.data['testcase'] = 'testcase2'
        self.data['username'] = 'foo'
        r = client.post('/api/v1.0/waivers/', data=json.dumps(self.data),
                        content_type='application/json', headers=self.headers)
        res_data = json.loads(r.get_data(as_text=True))
        assert r.status_code == 201
        assert res_data['username'] == 'foo'
        assert res_data['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
        assert res_data['subject_type'] == 'koji_build'
        assert res_data['subject_identifier'] == 'glibc-2.26-27.fc27'
        assert res_data['testcase'] == 'testcase2'
        assert res_data['product_version'] == 'fool-1'
        assert res_data['waived'] is True
        assert res_data['comment'] == 'it broke'
        assert res_data['proxied_by'] == 'bodhi'

    @pytest.mark.usefixtures('enable_ldap_host')
    @pytest.mark.usefixtures('enable_ldap_base')
    @mock.patch('waiverdb.auth.get_user', return_value=('bodhi', {}))
    @mock.patch('requests.request',
                side_effect=Unauthorized('You are not authorized to submit a waiver for the test '
                                         'case testcase3'))
    def test_proxied_by_with_no_permission_cli(self, mock_request, mock_get_user, client, session,
                                               tmpdir):
        p = tmpdir.join('client.conf')
        p.write(dedent("""
            [waiverdb]
            auth_method=Kerberos
            api_url=http://localhost:5004/api/v1.0
            """))
        self.data['testcase'] = 'testcase3'
        self.data['username'] = 'foo'
        runner = CliRunner()
        args = ['-C', p.strpath, '-s', '{"type": "koji_build", "item": "glibc-2.26-27.fc27"}',
                '-t', 'testcase3', '-c', 'This is fine', '-p', 'fool-1', '-u', 'foo']
        result = runner.invoke(waiverdb_cli, args, catch_exceptions=True)
        assert result.exception.description == ("You are not authorized to submit a waiver "
                                                "for the test case testcase3")

    @pytest.mark.usefixtures('enable_ldap_host')
    @pytest.mark.usefixtures('enable_ldap_base')
    @mock.patch('waiverdb.auth.get_user', return_value=('bodhi', {}))
    def test_proxied_by_has_permission_cli(self, mock_get_user, client, session, tmpdir):
        with mock.patch('requests.request') as mock_request:
            mock_rv = mock.Mock()
            mock_rv.json.return_value = [{
                "comment": "it broke",
                "data": {"item": ["glibc-2.26-27.fc27"], "type": ["koji_build"]},
                "id": 15,
                "product_version": "fool-1",
                "testcase": "testcase2",
                "timestamp": "2017-010-16T17:42:04.209638",
                "username": "foo",
                "proxied_by": "bodhi",
                "waived": True
            }]
            mock_request.return_value = mock_rv
            p = tmpdir.join('client.conf')
            p.write(dedent("""
                [waiverdb]
                auth_method=Kerberos
                api_url=http://localhost:5004/api/v1.0
                """))
            runner = CliRunner()
            args = ['-C', p.strpath, '-p', 'fool-1', '-r', '123',
                    '-c', "This is fine", '-u', 'foo']
            result = runner.invoke(waiverdb_cli, args)
            mock_request.assert_called_once()
            assert result.output.startswith('Created waiver 15 for result with id 123\n')
