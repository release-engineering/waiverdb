import requests


def test_new_waiver_with_token(waiverdb, keycloak):
    token_url = f"{keycloak}/realms/EmployeeIDP/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": "waiverdb",
        "client_secret": "nosecret",
    }
    response = requests.post(token_url, data=data)
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]

    waiver_url = f"{waiverdb}/api/v1.0/waivers/new"
    headers = {"Authorization": f"Bearer {token}"}
    waiver = {
        "subject_type": "component-version",
        "subject_identifier": "nethack-stage-3.5-1",
        "testcase": "test1",
        "waived": True,
        "product_version": "fedora-11",
        "comment": "This is a test",
    }
    response = requests.post(waiver_url, json=waiver, headers=headers)
    assert response.status_code == 201, response.text

    waiver["testcase"] = "xtest1"
    response = requests.post(waiver_url, json=waiver, headers=headers)
    assert response.status_code == 403, response.text
