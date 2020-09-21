# SPDX-License-Identifier: GPL-2.0+

import logging
import re

from werkzeug.exceptions import (
    BadGateway,
    InternalServerError,
    Unauthorized,
)

log = logging.getLogger(__name__)


def get_group_membership(user, ldap_host, ldap_base, search_string):
    try:
        import ldap
    except ImportError:
        raise InternalServerError(('If PERMISSION_MAPPING is defined, '
                                   'python-ldap needs to be installed.'))

    try:
        con = ldap.initialize(ldap_host)
        results = con.search_s(ldap_base, ldap.SCOPE_SUBTREE, search_string.format(user), ['cn'])
        return [group[1]['cn'][0].decode('utf-8') for group in results]
    except ldap.SERVER_DOWN:
        log.exception('The LDAP server is not reachable.')
        raise BadGateway('The LDAP server is not reachable.')
    except ldap.LDAPError:
        log.exception('Some error occurred initializing the LDAP connection.')
        raise Unauthorized('Some error occurred initializing the LDAP connection.')


def verify_authorization(user, testcase, permission_mapping, ldap_host, ldap_base, search_strings):
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

    ldap_hosts = ldap_host.split('|||')
    ldap_bases = ldap_base.split('|||')
    ldap_search_strings = search_strings.split('|||')

    group_membership = set()

    for i in range(max((len(ldap_hosts), len(ldap_bases), len(ldap_search_strings)))):
        ldap_host_cur = ldap_hosts[i % len(ldap_hosts)]
        ldap_base_cur = ldap_bases[i % len(ldap_bases)]
        search_string_cur = ldap_search_strings[i % len(ldap_search_strings)]
        group_membership.update(
            get_group_membership(user, ldap_host_cur, ldap_base_cur, search_string_cur)
        )
    if not group_membership:
        raise Unauthorized(f'Couldn\'t find user {user} in LDAP')

    if group_membership & set(allowed_groups):
        return True

    raise Unauthorized(('You are not authorized to submit a waiver '
                        f'for the test case {testcase}'))
