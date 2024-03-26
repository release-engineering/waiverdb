# SPDX-License-Identifier: GPL-2.0+
from selenium.webdriver.support.expected_conditions import visibility_of
from selenium.webdriver.support.wait import WebDriverWait

SUBMIT_TIMEOUT_SECONDS = 10


def test_new_waiver_form(selenium, waiverdb, keycloak, login):
    url = (
        f"{waiverdb}/api/v1.0/waivers/new"
        "?testcase=test&product_version=pv"
        "&subject_identifier=item&subject_type=type"
        "&comment=comment"
    )
    selenium.get(url)
    assert selenium.current_url.startswith(keycloak)
    login()
    assert selenium.current_url == url

    assert selenium.find_element("name", "testcase").get_property("value") == "test"
    assert selenium.find_element("name", "product_version").get_property("value") == "pv"
    assert selenium.find_element("name", "subject_identifier").get_property("value") == "item"
    assert selenium.find_element("name", "subject_type").get_property("value") == "type"
    assert selenium.find_element("name", "comment").get_property("value") == "comment"

    banner = selenium.find_element("id", "waiver-result")
    assert not banner.is_displayed()

    selenium.find_element("id", "new-waiver-form").submit()
    assert selenium.current_url == url

    WebDriverWait(selenium, SUBMIT_TIMEOUT_SECONDS).until(visibility_of(banner))
    assert banner.is_displayed()
    assert banner.text.startswith("New waiver created. ID: ")


def test_new_waiver_form_missing_permission(selenium, waiverdb, keycloak, login):
    url = f"{waiverdb}/api/v1.0/waivers/new?testcase=other_test"
    selenium.get(url)
    assert selenium.current_url.startswith(keycloak)
    login()
    assert selenium.current_url == url

    alert = selenium.find_element("id", "other-error")
    assert alert.is_displayed()
    assert alert.text == (
        "403 Forbidden: User admin is not authorized to submit results for"
        " the test case other_test\n"
        "See who has permission to waive other_test test case."
    )
