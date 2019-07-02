# SPDX-License-Identifier: GPL-2.0+

import logging
import re

from werkzeug.exceptions import (
    BadGateway,
    InternalServerError,
    Unauthorized,
)

log = logging.getLogger(__name__)


def get_group_membership(user, ldap_host, ldap_base):
    try:
        import ldap
    except ImportError:
        raise InternalServerError(('If PERMISSION_MAPPING is defined, '
                                   'python-ldap needs to be installed.'))

    try:
        con = ldap.initialize(ldap_host)
        results = con.search_s(ldap_base, ldap.SCOPE_SUBTREE, f'(memberUid={user})', ['cn'])
        return [group[1]['cn'][0].decode('utf-8') for group in results]
    except ldap.LDAPError:
        log.exception('Some error occurred initializing the LDAP connection.')
        raise Unauthorized('Some error occurred initializing the LDAP connection.')
    except ldap.SERVER_DOWN:
        log.exception('The LDAP server is not reachable.')
        raise BadGateway('The LDAP server is not reachable.')


def verify_authorization(user, testcase, permission_mapping, ldap_host, ldap_base):
    if not (ldap_host and ldap_base):
        raise InternalServerError(('LDAP_HOST and LDAP_BASE also need to be defined '
                                   'if PERMISSION_MAPPING is defined.'))

    allowed_groups = []
    for testcase_pattern, permission in permission_mapping.items():
        testcase_match = re.search(testcase_pattern, testcase)
        if testcase_match:
            # checking if the user is allowed
            if user in permission['users']:
                return True
            allowed_groups += permission['groups']

    group_membership = get_group_membership(user, ldap_host, ldap_base)
    if not group_membership:
        raise Unauthorized(f'Couldn\'t find user {user} in LDAP')

    if set(group_membership) & set(allowed_groups):
        return True

    raise Unauthorized(('You are not authorized to submit a waiver '
                        f'for the test case {testcase}'))
