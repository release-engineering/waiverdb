"""
Functional tests for OIDC group-based authorization.

Requires the Keycloak realm to have:
- A "waiverdb-users" realm role
- The service-account-waiverdb user assigned to that role

And WaiverDB settings with a permission like:
    {"testcases": ["oidc-group-test.*"], "groups": ["waiverdb-users"]}
"""
import requests


def _get_token(keycloak):
    token_url = f"{keycloak}/realms/EmployeeIDP/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": "waiverdb",
        "client_secret": "nosecret",
    }
    response = requests.post(token_url, data=data)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_oidc_groups_authorize(waiverdb, keycloak):
    """Service account with waiverdb-users role can waive via OIDC groups."""
    token = _get_token(keycloak)
    headers = {"Authorization": f"Bearer {token}"}
    waiver = {
        "subject_type": "component-version",
        "subject_identifier": "test-component-1.0-1",
        "testcase": "oidc-group-test.smoke",
        "waived": True,
        "product_version": "fedora-99",
        "comment": "Authorized via OIDC group",
    }
    response = requests.post(
        f"{waiverdb}/api/v1.0/waivers/", json=waiver, headers=headers, timeout=60,
    )
    assert response.status_code == 201, response.text


def test_oidc_groups_deny_missing_role(waiverdb, keycloak):
    """Service account without the required role is denied."""
    token = _get_token(keycloak)
    headers = {"Authorization": f"Bearer {token}"}
    waiver = {
        "subject_type": "component-version",
        "subject_identifier": "test-component-1.0-1",
        "testcase": "xtest-no-permission",
        "waived": True,
        "product_version": "fedora-99",
        "comment": "Should be denied",
    }
    response = requests.post(
        f"{waiverdb}/api/v1.0/waivers/", json=waiver, headers=headers, timeout=60,
    )
    assert response.status_code == 403, response.text
