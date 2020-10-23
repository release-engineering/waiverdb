# SPDX-License-Identifier: GPL-2.0+

import logging
import re

from werkzeug.exceptions import (
    BadGateway,
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


def verify_authorization(user, testcase, permission_mapping, ldap_host, ldap_searches):
    if not (ldap_host and ldap_searches):
        raise InternalServerError(('LDAP_HOST and LDAP_SEARCHES also need to be defined '
                                   'if PERMISSION_MAPPING is defined.'))

    allowed_groups = []
    for testcase_pattern, permission in permission_mapping.items():
        testcase_match = re.search(testcase_pattern, testcase)
        if testcase_match:
            # checking if the user is allowed
            if user in permission['users']:
                return True
            allowed_groups += permission['groups']

    try:
        import ldap
    except ImportError:
        raise InternalServerError(('If PERMISSION_MAPPING is defined, '
                                   'python-ldap needs to be installed.'))

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
        raise Unauthorized(f'Couldn\'t find user {user} in LDAP')

    raise Unauthorized(('You are not authorized to submit a waiver '
                        f'for the test case {testcase}'))
