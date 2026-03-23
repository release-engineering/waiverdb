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


def _check_oidc_groups(user, testcase, oidc_groups, allowed_groups):
    """Check OIDC group membership. Returns True if authorized, False to fall back."""
    if oidc_groups is None:
        return False

    if not oidc_groups:
        log.warning(
            "OIDC token for user %s contains an empty groups claim; "
            "falling back to LDAP for test case %s",
            user, testcase,
        )
        return False

    if not set(oidc_groups).isdisjoint(allowed_groups):
        return True

    log.warning(
        "OIDC groups %r did not match any allowed groups %r for user %s "
        "and test case %s; falling back to LDAP",
        oidc_groups, allowed_groups, user, testcase,
    )
    return False


def _check_ldap_groups(user, testcase, ldap_host, ldap_searches, allowed_groups):
    """
    Check LDAP group membership.

    Returns True if authorized, False if LDAP is not configured.
    """
    if not ldap_host or not ldap_searches:
        return False

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
            return True

    if not group_membership:
        raise Forbidden(
            description=(
                f"User {user} is not authorized to submit results"
                f" for the test case {testcase}; failed to find the user in LDAP"
            )
        )

    return False


def verify_authorization(
    user: str, testcase: str, permissions: list[dict[str, Any]],
    ldap_host: str, ldap_searches: list[dict[str, str]],
    oidc_groups: list[str] | None = None,
):
    allowed_groups = []
    for permission in match_testcase_permissions(testcase, permissions):
        if user in permission.get('users', []):
            return
        allowed_groups += permission.get('groups', [])

    if _check_oidc_groups(user, testcase, oidc_groups, allowed_groups):
        return

    if _check_ldap_groups(user, testcase, ldap_host, ldap_searches, allowed_groups):
        if oidc_groups is not None:
            log.warning(
                "LDAP authorized user %s for test case %s. "
                "Consider adding the appropriate groups to the user's "
                "OIDC token to avoid LDAP dependency.",
                user, testcase,
            )
        return

    raise Forbidden(
        description=(
            f"User {user} is not authorized to submit results for the test case {testcase}"
        )
    )
