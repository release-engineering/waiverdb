# SPDX-License-Identifier: GPL-2.0+
import re


def test_oidc_login(selenium, waiverdb, login):
    login_url = f"{waiverdb}/auth/oidclogin"
    # JSON can be represented in web browser in a formatted way
    expected_content = re.compile('email.*"noreply@example.com".*token.*"ey')

    login(login_url)
    assert expected_content.search(selenium.page_source)

    # No login required the second time
    selenium.get(login_url)
    assert expected_content.search(selenium.page_source)
