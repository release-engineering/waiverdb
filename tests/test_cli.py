# SPDX-License-Identifier: GPL-2.0+
import pytest
import json
from mock import Mock, patch
from click.testing import CliRunner
from waiverdb.cli import cli as waiverdb_cli
from waiverdb.cli import guess_product_version


def test_misconfigured_auth_method(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
api_url=http://localhost:5004/api/v1.0
        """)
    runner = CliRunner()
    args = ['-C', p.strpath]
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code == 1
    assert result.output == 'Error: The config option "auth_method" is required\n'


def test_misconfigured_api_url(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=OIDC
        """)
    runner = CliRunner()
    args = ['-C', p.strpath]
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code == 1
    assert result.output == 'Error: The config option "api_url" is required\n'


def test_misconfigured_oidc_id_provider(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=OIDC
api_url=http://localhost:5004/api/v1.0
        """)
    runner = CliRunner()
    args = ['-C', p.strpath]
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code == 1
    assert result.output == 'Error: The config option "oidc_id_provider" is required\n'


def test_misconfigured_oidc_client_id(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=OIDC
api_url=http://localhost:5004/api/v1.0
oidc_id_provider=https://id.stg.fedoraproject.org/openidc/
        """)
    runner = CliRunner()
    args = ['-C', p.strpath]
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code == 1
    assert result.output == 'Error: The config option "oidc_client_id" is required\n'


def test_misconfigured_oidc_scopes(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=OIDC
api_url=http://localhost:5004/api/v1.0
oidc_id_provider=https://id.stg.fedoraproject.org/openidc/
oidc_client_id=waiverdb
        """)
    runner = CliRunner()
    args = ['-C', p.strpath]
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code == 1
    assert result.output == 'Error: The config option "oidc_scopes" is required\n'


def test_no_product_version(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=OIDC
api_url=http://localhost:5004/api/v1.0
oidc_id_provider=https://id.stg.fedoraproject.org/openidc/
oidc_client_id=waiverdb
oidc_scopes=
    openid
        """)
    runner = CliRunner()
    args = ['-C', p.strpath, '-i', 'test', '-T', 'compose', '-t', 'testcase',
            '-c', 'comment']
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code == 1
    assert result.output == 'Error: Please specify product version using --product-version\n'


def test_no_subject(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=OIDC
api_url=http://localhost:5004/api/v1.0
oidc_id_provider=https://id.stg.fedoraproject.org/openidc/
oidc_client_id=waiverdb
oidc_scopes=
    openid
        """)
    runner = CliRunner()
    args = ['-C', p.strpath, '-p', 'fedora-26', '-c', 'comment']
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code == 1
    assert result.output == 'Error: Please specify subject-identifier\n'


def test_no_testcase(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=OIDC
api_url=http://localhost:5004/api/v1.0
oidc_id_provider=https://id.stg.fedoraproject.org/openidc/
oidc_client_id=waiverdb
oidc_scopes=
    openid
        """)
    runner = CliRunner()
    args = ['-C', p.strpath, '-p', 'fedora-26', '-i', 'item', '-T', 'compose', '-c', 'comment']
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code == 1
    assert result.output == 'Error: Please specify testcase\n'


def test_no_comment(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=OIDC
api_url=http://localhost:5004/api/v1.0
oidc_id_provider=https://id.stg.fedoraproject.org/openidc/
oidc_client_id=waiverdb
oidc_scopes=
    openid
        """)
    runner = CliRunner()
    args = ['-C', p.strpath, '-p', 'fedora-26', '-i', 'item', '-T', 'compose', '-t', 'testcase']
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code == 1
    assert result.output == 'Error: Please specify comment\n'


def test_oidc_auth_is_enabled(tmpdir):
    # Skip if waiverdb is rebuilt for an environment where GSSAPI
    # authentication is used and python-openidc-client is not available.
    pytest.importorskip('openidc_client')
    with patch('openidc_client.OpenIDCClient.send_request') as mock_oidc_req:
        mock_rv = Mock()
        mock_rv.json.return_value = [{
            "comment": "This is fine",
            "data": {"item": ["htop-1.0-1.fc22"], "type": ["bodhi_update"]},
            "id": 15,
            "product_version": "Parrot",
            "testcase": "test.testcase",
            "timestamp": "2017-010-16T17:42:04.209638",
            "username": "foo",
            "waived": True
        }]
        mock_oidc_req.return_value = mock_rv
        p = tmpdir.join('client.conf')
        p.write("""
[waiverdb]
auth_method=OIDC
api_url=http://localhost:5004/api/v1.0
oidc_id_provider=https://id.stg.fedoraproject.org/openidc/
oidc_client_id=waiverdb
oidc_scopes=
    openid
            """)
        runner = CliRunner()
        args = ['-C', p.strpath, '-p', 'Parrot', '-r', '123',
                '-c', "This is fine"]
        result = runner.invoke(waiverdb_cli, args)
        exp_json = [{
            "result_id": 123,
            "waived": True,
            "product_version": "Parrot",
            "comment": "This is fine",
            "username": None
        }]
        mock_oidc_req.assert_called_once_with(
            url='http://localhost:5004/api/v1.0/waivers/',
            data=json.dumps(exp_json),
            scopes=['openid'],
            timeout=60,
            headers={'Content-Type': 'application/json'})
        assert result.exit_code == 0
        assert result.output.startswith('Created waiver 15 for result with id 123\n')


def test_gssapi_is_enabled(tmpdir):
    with patch('requests.request') as mock_request:
        mock_rv = Mock()
        mock_rv.json.return_value = [{
            "comment": "This is fine",
            "data": {"item": ["htop-1.0-1.fc22"], "type": ["bodhi_update"]},
            "id": 15,
            "product_version": "Parrot",
            "testcase": "test.testcase",
            "timestamp": "2017-010-16T17:42:04.209638",
            "username": "foo",
            "waived": True
        }]
        mock_request.return_value = mock_rv
        p = tmpdir.join('client.conf')
        p.write("""
[waiverdb]
auth_method=Kerberos
api_url=http://localhost:5004/api/v1.0
            """)
        runner = CliRunner()
        args = ['-C', p.strpath, '-p', 'Parrot', '-r', '123',
                '-c', "This is fine"]
        result = runner.invoke(waiverdb_cli, args)
        mock_request.assert_called_once()
        assert result.output.startswith('Created waiver 15 for result with id 123\n')


def test_submit_waiver_with_id(tmpdir):
    with patch('requests.request') as mock_request:
        mock_rv = Mock()
        mock_rv.json.return_value = [{
            "comment": "This is fine",
            "data": {"item": ["htop-1.0-1.fc22"], "type": ["bodhi_update"]},
            "id": 15,
            "product_version": "Parrot",
            "testcase": {"name": "test.testcase"},
            "timestamp": "2017-010-16T17:42:04.209638",
            "username": "foo",
            "waived": True
        }]
        mock_request.return_value = mock_rv
        p = tmpdir.join('client.conf')
        p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
        """)
        runner = CliRunner()
        args = ['-C', p.strpath, '-p', 'Parrot', '-r', '123',
                '-c', "This is fine"]
        result = runner.invoke(waiverdb_cli, args, catch_exceptions=False)
        mock_request.assert_called()
        assert result.output == 'Created waiver 15 for result with id 123\n'


def test_submit_waiver_with_multiple_ids(tmpdir):
    with patch('requests.request') as mock_request:
        mock_rv = Mock()
        mock_rv.json.return_value = [
            {
                "comment": "This is fine",
                "data": {"item": ["htop-1.0-1.fc22"], "type": ["bodhi_update"]},
                "id": 15,
                "testcase": {"name": "test.testcase"},
                "timestamp": "2017-010-16T17:42:04.209638",
                "username": "foo",
                "waived": True
            }, {
                "comment": "This is fine",
                "data": {"item": ["htop-1.0-2.fc22"], "type": ["bodhi_update"]},
                "id": 16,
                "testcase": {"name": "test.testcase"},
                "timestamp": "2017-010-16T17:42:04.209638",
                "username": "foo",
                "waived": True
            }
        ]
        mock_request.return_value = mock_rv
        p = tmpdir.join('client.conf')
        p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
        """)
        runner = CliRunner()
        args = ['-C', p.strpath, '-p', 'Parrot', '-r', '123', '-r', '456',
                '-c', "This is fine"]
        result = runner.invoke(waiverdb_cli, args, catch_exceptions=False)
        mock_request.assert_called()

        assert result.output == 'Created waiver 15 for result with id 123\n\
Created waiver 16 for result with id 456\n'


def test_malformed_submission_with_id_and_subject_and_testcase(tmpdir):
    runner = CliRunner()
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
    """)
    args = ['-C', p.strpath, '-p', 'Parrot', '-r', '123', '-s',
            '{"subject.test": "test", "s": "t"}', '-c', "This is fine"]
    result = runner.invoke(waiverdb_cli, args, catch_exceptions=False)
    assert result.output == 'Error: Please specify result_id or subject/testcase. Not both\n'


def test_submit_waiver_for_original_spec_nvr_result(tmpdir):
    with patch('requests.request') as mock_request:
        mock_rv = Mock()
        mock_rv.json.return_value = [{
            "comment": "This is fine",
            "original_spec_nvr": "test",
            "id": 15,
            "product_version": "Parrot",
            "testcase": {"name": "test.testcase"},
            "timestamp": "2017-010-16T17:42:04.209638",
            "username": "foo",
            "waived": True
        }]
        mock_request.return_value = mock_rv
        p = tmpdir.join('client.conf')
        p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
            """)
        runner = CliRunner()
        args = ['-C', p.strpath, '-p', 'Parrot', '-r', '123',
                '-c', "This is fine"]
        result = runner.invoke(waiverdb_cli, args)
        mock_request.assert_called()
        assert result.output == 'Created waiver 15 for result with id 123\n'


def test_create_waiver_product_version_missing(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
koji_base_url=https://koji.fedoraproject.org/kojihub
    """)
    runner = CliRunner()
    args = ['-C', p.strpath, '-s', '{"type": "koji_build", "item": "this-will-not-work"}',
            '-t', 'test.testcase', '-c', "This is fine"]
    result = runner.invoke(waiverdb_cli, args)
    assert result.output == 'Error: Please specify product version using --product-version\n'


def test_create_waiver_product_version_from_koji_build(tmpdir):
    with patch('requests.request') as mock_request:
        mock_rv = Mock()
        mock_rv.json.return_value = [{
            "comment": "This is fine",
            "id": 15,
            "subject_type": "koji_build",
            "subject_identifier": "setup-2.8.71-7.el7_4",
            "testcase": "test.testcase",
            "timestamp": "2017-010-16T17:42:04.209638",
            "username": "foo",
            "waived": True
        }]
        mock_request.return_value = mock_rv
        p = tmpdir.join('client.conf')
        p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
koji_base_url=https://koji.fedoraproject.org/kojihub
        """)
        runner = CliRunner()
        args = ['-C', p.strpath, '-s', '{"type": "koji_build", "item": "setup-2.8.71-7.el7_4"}',
                '-t', 'test.testcase', '-c', "This is fine"]
        result = runner.invoke(waiverdb_cli, args, catch_exceptions=False)
        mock_request.assert_called()
        assert result.output == (
            'Created waiver 15 for result with '
            'subject type koji_build, identifier setup-2.8.71-7.el7_4 '
            'and testcase test.testcase\n'
        )


def test_create_waiver_product_version_from_compose(tmpdir):
    with patch('requests.request') as mock_request:
        mock_rv = Mock()
        mock_rv.json.return_value = [{
            "comment": "This is fine",
            "id": 15,
            "subject_type": "compose",
            "subject_identifier": "Fedora-Rawhide-20180526.n.1",
            "testcase": "test.testcase",
            "timestamp": "2017-010-16T17:42:04.209638",
            "username": "foo",
            "waived": True
        }]
        mock_request.return_value = mock_rv
        p = tmpdir.join('client.conf')
        p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
koji_base_url=https://koji.fedoraproject.org/kojihub
        """)
        runner = CliRunner()
        args = ['-C', p.strpath, '-s', ('{"productmd.compose.id": "Fedora-Rawhide-20180526.n.1",'
                                        '"type": "compose",'
                                        '"item": "Fedora-Rawhide-20180526.n.1"}'),
                '-t', 'test.testcase', '-c', "This is fine"]
        result = runner.invoke(waiverdb_cli, args)
        mock_request.assert_called()
        assert result.output == (
            'Created waiver 15 for result with '
            'subject type compose, identifier Fedora-Rawhide-20180526.n.1 '
            'and testcase test.testcase\n'
        )


def test_guess_product_version():
    # some more tests for checking "guess_product_version"
    assert guess_product_version('epel7-infra-mailman') == 'epel-7'
    assert guess_product_version('f26-infra', koji_build=True) == 'fedora-26'
    assert guess_product_version('Fedora-28-20180423.n.0') == 'fedora-28'
    assert guess_product_version('Fedora-Rawhide-20180524.n.0') == 'fedora-rawhide'
    assert guess_product_version('Fedora-Atomic-28-20180424.4') is None


def test_create_waiver_missing_subject_identifier(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
koji_base_url=https://koji.fedoraproject.org/kojihub
    """)
    runner = CliRunner()
    args = ['-C', p.strpath, '-T', 'koji_build',
            '-t', 'test.testcase', '-c', "This is fine"]
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code != 0
    assert 'Error: Please specify subject-identifier' in result.output


def test_create_waiver_missing_subject_type(tmpdir):
    p = tmpdir.join('client.conf')
    p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
koji_base_url=https://koji.fedoraproject.org/kojihub
    """)
    runner = CliRunner()
    args = ['-C', p.strpath, '-i', 'setup-2.8.71-7.el7_4',
            '-t', 'test.testcase', '-c', "This is fine"]
    result = runner.invoke(waiverdb_cli, args)
    assert result.exit_code != 0
    assert 'Error: Please specify subject_type' in result.output


def test_submit_waiver_with_arbitrary_subject_type(tmpdir):
    with patch('requests.request') as mock_request:
        mock_rv = Mock()
        mock_rv.json.return_value = [{
            "comment": "This is fine",
            "id": 15,
            "product_version": "Parrot",
            "subject_type": "some-kind-of-magic",
            "subject_identifier": "setup-2.8.71-7.el7_4",
            "testcase": "test.testcase",
            "timestamp": "2017-010-16T17:42:04.209638",
            "username": "foo",
            "waived": True
        }]
        mock_request.return_value = mock_rv
        p = tmpdir.join('client.conf')
        p.write("""
[waiverdb]
auth_method=dummy
api_url=http://localhost:5004/api/v1.0
            """)
        runner = CliRunner()
        args = ['-C', p.strpath, '-p', 'Parrot',
                '-s', '{"type": "some-kind-of-magic", "item": "setup-2.8.71-7.el7_4"}',
                '-t', 'test.testcase', '-c', "This is fine"]
        result = runner.invoke(waiverdb_cli, args)
        mock_request.assert_called()
        assert result.output == ('Created waiver 15 for result with subject type '
                                 'some-kind-of-magic, identifier setup-2.8.71-7.el7_4 and '
                                 'testcase test.testcase\n')
