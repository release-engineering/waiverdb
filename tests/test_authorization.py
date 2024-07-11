from ldap import LDAPError
from pytest import raises
from unittest.mock import patch
from waiverdb.api_v1 import permissions
from waiverdb.authorization import match_testcase_permissions, verify_authorization
from werkzeug.exceptions import Forbidden, Unauthorized


# Sample data and permissions for testing
test_permissions = [
    {
        'users': ['authorized_user'],
        'groups': ['authorized_group'],
        'testcases': ['test_case_1'],
    },
    {
        'users': [],
        'groups': ['authorized_group'],
        'testcases_ignore': ['ignore_case'],
    },
    {
        '_testcase_regex_pattern': r'test_case_\d+',
        'users': [],
        'groups': ['authorized_group'],
    },
]

ldap_searches = ['ldap_search_1']
ldap_host = 'ldap://example.com'


# Mock function to simulate group membership lookup
def mock_get_group_membership(ldap, user, con, search) -> list[str]:
    if user == 'group_user':
        return ['authorized_group']
    return []


class TestVerifyAuthorization:
    @patch('ldap.initialize')
    @patch('waiverdb.authorization.get_group_membership', side_effect=mock_get_group_membership)
    def test_user_authorized(self, mock_ldap, mock_get_group):
        verify_authorization(
            'authorized_user', 'test_case_1', test_permissions, ldap_host, ldap_searches
        )

    @patch('ldap.initialize')
    @patch('waiverdb.authorization.get_group_membership', side_effect=mock_get_group_membership)
    def test_user_in_group_authorized(self, mock_ldap, mock_get_group):
        verify_authorization(
            'group_user', 'test_case_1', test_permissions, ldap_host, ldap_searches
        )

    @patch('ldap.initialize')
    @patch('waiverdb.authorization.get_group_membership', side_effect=mock_get_group_membership)
    def test_user_not_authorized(self, mock_ldap, mock_get_group):
        with raises(Forbidden) as exc_info:
            verify_authorization(
                'unauthorized_user', 'test_case_1', test_permissions, ldap_host, ldap_searches
            )
        assert "User unauthorized_user is not authorized" in str(exc_info.value)

    @patch('ldap.initialize', side_effect=LDAPError('LDAP connection error'))
    def test_ldap_connection_error(self, mock_ldap):
        with raises(Unauthorized) as exc_info:
            verify_authorization(
                'unauthorized_user', 'test_case_1', test_permissions, ldap_host, ldap_searches
            )
        assert "Some error occurred initializing the LDAP connection." in str(exc_info.value)

    def test_no_ldap_configuration(self):
        with raises(Forbidden) as exc_info:
            verify_authorization('unauthorized_user', 'test_case_1', test_permissions, None, None)
        assert "User unauthorized_user is not authorized" in str(exc_info.value)

    @patch('ldap.initialize')
    @patch('waiverdb.authorization.get_group_membership', side_effect=mock_get_group_membership)
    def test_testcase_ignore(self, mock_ldap, mock_get_group):
        with raises(Forbidden) as exc_info:
            verify_authorization(
                'unauthorized_user', 'ignore_case', test_permissions, ldap_host, ldap_searches
            )
        assert "User unauthorized_user is not authorized" in str(exc_info.value)

    @patch('ldap.initialize')
    @patch('waiverdb.authorization.get_group_membership', side_effect=mock_get_group_membership)
    def test_testcase_regex_pattern(self, mock_ldap, mock_get_group):
        with raises(Forbidden) as exc_info:
            verify_authorization(
                'unauthorized_user', 'test_case_999', test_permissions, ldap_host, ldap_searches
            )
        assert "User unauthorized_user is not authorized" in str(exc_info.value)


def test_permissions_mapping_compat(app, monkeypatch):
    """
    Verify backwards compatibility with deprecated PERMISSION_MAPPING option.
    """
    monkeypatch.setitem(app.config, 'PERMISSIONS', [])
    monkeypatch.setitem(app.config, 'PERMISSION_MAPPING', {})
    assert permissions() == []

    permission_mapping = {
        "^kernel-qe": {
            "groups": ["devel", "qa"],
            "users": ["alice@example.com"],
            "maintainer": "alice@example.com",
        },
    }
    monkeypatch.setitem(app.config, 'PERMISSION_MAPPING', permission_mapping)
    assert permissions() == [
        {
            "name": "^kernel-qe",
            "maintainers": ["alice@example.com"],
            "_testcase_regex_pattern": "^kernel-qe",
            "groups": ["devel", "qa"],
            "users": ["alice@example.com"],
        }
    ]

    permissions_override = [
        {
            "name": "Greenwave Tests",
            "maintainers": ["greenwave-dev@example.com"],
            "testcases": ["greenwave-tests.*"],
            "groups": [],
            "users": ["HTTP/greenwave-dev.tests.example.com"]
        }
    ]
    monkeypatch.setitem(app.config, 'PERMISSIONS', permissions_override)
    assert permissions() == permissions_override


def test_match_testcase_permissions():
    """
    Verify that correct permissions are retrieved for given test case name.
    """
    assert list(match_testcase_permissions("kernel-qe.test1", [])) == []

    permissions = [
        {
            "name": "^kernel-qe",
            "maintainers": ["alice@example.com"],
            "_testcase_regex_pattern": "^kernel-qe",
            "groups": ["devel", "qa"],
            "users": ["alice@example.com"],
        },
        {
            "name": "Greenwave Tests",
            "maintainers": ["greenwave-dev@example.com"],
            "testcases": ["greenwave-tests.*"],
            "groups": [],
            "users": ["HTTP/greenwave-dev.tests.example.com"]
        }
    ]
    assert list(match_testcase_permissions("greenwave-tests.test1", permissions)) \
        == [permissions[1]]
    assert list(match_testcase_permissions("kernel-qe.test1", permissions)) \
        == [permissions[0]]
