# SPDX-License-Identifier: GPL-2.0+
def test_oidc_login(selenium, waiverdb, keycloak, login):
    login_url = f"{waiverdb}/auth/oidclogin"

    selenium.get(login_url)
    assert selenium.current_url.startswith(keycloak)
    login()
    assert selenium.current_url == login_url

    expected_content = '{"email":"noreply@example.com","token":"ey' 
    assert expected_content in selenium.page_source

    # No login required the second time
    selenium.get(login_url)
    assert expected_content in selenium.page_source
