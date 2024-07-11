# SPDX-License-Identifier: GPL-2.0+

import logging
import re
from fnmatch import fnmatch
from typing import Any

from werkzeug.exceptions import (
    BadGateway,
    Forbidden,
    InternalServerError,
    Unauthorized,
)

log = logging.getLogger(__name__)


def get_group_membership(ldap, user, con, ldap_search):
    try:
        results = con.search_s(
            ldap_search['BASE'], ldap.SCOPE_SUBTREE,
            ldap_search.get('SEARCH_STRING', '(memberUid={user})').format(user=user), ['cn']
        )
        return [group[1]['cn'][0].decode('utf-8') for group in results]
    except KeyError:
        log.exception('LDAP_SEARCHES parameter should contain the BASE key')
        raise InternalServerError('LDAP_SEARCHES parameter should contain the BASE key')
    except ldap.SERVER_DOWN:
        log.exception('The LDAP server is not reachable.')
        raise BadGateway('The LDAP server is not reachable.')
    except ldap.LDAPError:
        log.exception('Some error occurred initializing the LDAP connection.')
        raise Unauthorized('Some error occurred initializing the LDAP connection.')


def match_testcase(testcase: str, patterns: list[str]):
    return any(fnmatch(testcase, pattern) for pattern in patterns)


def match_testcase_permissions(testcase: str, permissions: list[dict[str, Any]]):
    for permission in permissions:
        if match_testcase(testcase, permission.get("testcases_ignore", [])):
            continue

        if "testcases" in permission:
            testcase_match = match_testcase(testcase, permission["testcases"])
        elif "_testcase_regex_pattern" in permission:
            testcase_match = re.search(
                permission["_testcase_regex_pattern"], testcase)
        else:
            continue

        if testcase_match:
            yield permission


def verify_authorization(
    user: str, testcase: str, permissions: list[dict[str, Any]],
    ldap_host: str, ldap_searches: list[dict[str, str]],
):
    allowed_groups = []
    for permission in match_testcase_permissions(testcase, permissions):
        if user in permission.get('users', []):
            return
        allowed_groups += permission.get('groups', [])

    detail = ""
    if ldap_host and ldap_searches:
        import ldap

        try:
            con = ldap.initialize(ldap_host)
        except ldap.LDAPError:
            log.exception('Some error occurred initializing the LDAP connection.')
            raise Unauthorized('Some error occurred initializing the LDAP connection.')

        group_membership = set()

        for cur_ldap_search in ldap_searches:
            group_membership.update(
                get_group_membership(ldap, user, con, cur_ldap_search)
            )
            if group_membership & set(allowed_groups):
                return

        if not group_membership:
            detail = "; failed to find the user in LDAP"

    raise Forbidden(
        description=(
            f"User {user} is not authorized to submit results for the test case {testcase}"
            + detail
        )
    )
