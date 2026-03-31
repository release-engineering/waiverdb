.. _admin-guide:

===================
Administrator Guide
===================

This document describes configuration of WaiverDB server.

.. _auth:

Authentication
==============

Option ``AUTH_METHOD`` is name of authentication method. This can be "OIDC",
"Kerberos" or "SSL".

.. note:: Special name "dummy", used in development, authorizes any user.

.. _permissions:

Waive Permission
================

If ``PERMISSIONS`` option (and ``PERMISSION_MAPPING`` deprecated option) is
unset, anyone is able to waive any test result.

If the option is set, it describes which users and groups can waive which test
cases. Field ``testcases`` contains a glob expression to match test case names
and map them to ``groups`` and/or ``users``.

It is helpful to include metadata about permissions: ``name``,
``maintainer`` and ``description``.

When using OIDC authentication, group membership can be extracted directly
from the OIDC token. Option ``OIDC_GROUPS_FIELD`` (default
``'realm_access.roles'``) specifies the claim name in the OIDC token that
contains the user's groups. Dotted paths are supported for nested claims
(e.g. ``'realm_access.roles'``). If the claim is present and the groups
match, authorization succeeds without contacting LDAP. If the claim is
absent or groups don't match, LDAP is used as a fallback.

LDAP needs to be properly configured (i.e. options ``LDAP_HOST`` and
``LDAP_BASE``) for the fallback to work.

.. code-block:: python

    PERMISSIONS = {
        {
            "name": "kernel-qe",
            "maintainers": ["alice@example.com"],
            "testcases": ["kernel-qe.*"],
            "groups": ["devel", "qa"],
            "users": ["alice@example.com"]
        },
        {
            "name": "Admins",
            "maintainers": ["bob@example.com"],
            "testcases": ["*"],
            "groups": ["waiverdb-admins"]
        }
    }
    LDAP_HOST = 'ldap://ldap.example.com'
    LDAP_BASE = 'ou=Groups,dc=example,dc=com'

Option ``SUPERUSERS`` is a list of users who can waive results in place of
other users (which still require to have the permission). The superuser name is
then stored in the waiver under ``proxied_by`` field.

You can list the current permission mapping and list of superusers with
:http:get:`/api/v1.0/config`.

.. _cors:

Waive from Web UI
=================

WaiverDB uses `flask-cors
<https://flask-cors.readthedocs.io/en/latest/index.html>`__ to enable `CORS
<https://en.wikipedia.org/wiki/Cross-origin_resource_sharing>`__. This allows
web browsers to tell which web sites can safely waive.

There are couple of important `flask-cors options <https://flask-cors.readthedocs.io/en/latest/api.html#flask_cors.CORS>`__.

Option ``CORS_ORIGINS`` is a list of origins (it can be also string, a single
origin). This default to ``*`` which means all origins. The can also contain
regular expressions to match origins.

Option ``CORS_SUPPORTS_CREDENTIALS``, if set to ``True``, allows users to make
authenticated requests.

.. code-block:: python

    CORS_ORIGINS = [
        "https://bodhi.fedoraproject.org",
        "https://dashboard.example.com",
    ]
    CORS_SUPPORTS_CREDENTIALS = True

Deprecated option ``CORS_URL`` overrides ``CORS_ORIGINS``.
