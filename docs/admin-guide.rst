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

LDAP needs to be properly configured (i.e. options ``LDAP_HOST`` and
``LDAP_BASE``).

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
