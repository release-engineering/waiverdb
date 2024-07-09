# SPDX-License-Identifier: GPL-2.0+

import os

from pytest import fixture


@fixture
def chrome_options(chrome_options):
    chrome_options.add_argument('--headless')
    return chrome_options


@fixture
def firefox_options(firefox_options):
    firefox_options.add_argument("--headless")
    return firefox_options


@fixture
def selenium(selenium):
    selenium.delete_all_cookies()
    return selenium


@fixture
def waiverdb():
    return os.environ["WAIVERDB_TEST_URL"]


@fixture
def keycloak():
    return os.environ["KEYCLOAK_TEST_URL"]


@fixture
def login(selenium):
    def wrapped():
        selenium.find_element("id", "username").send_keys("admin")
        selenium.find_element("id", "password").send_keys("admin")
        selenium.find_element("name", "login").click()
    yield wrapped
