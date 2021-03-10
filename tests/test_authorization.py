from waiverdb.api_v1 import permissions
from waiverdb.authorization import match_testcase_permissions


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
