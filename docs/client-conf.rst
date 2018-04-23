.. _client-conf:

==========================
waiverdb-cli Configuration
==========================

Description
===========

The file :file:`/etc/waiverdb/client.conf` contains configuration for
:ref:`waiverdb-cli(1) <waiverdb-cli>`, a tool for reading and modifying
WaiverDB.

Options
=======

``[waiverdb]`` - Configuration section for ``waiverdb-cli``

``api_url`` - Base URL for WaiverDB API

``auth_method`` - Authentication method - ``OIDC`` (OpenID Connect) or ``Kerberos``

Following options are valid only if ``auth_method`` is set to ``OIDC``.

``oidc_id_provider`` - URL of the identity provider for OIDC to get tokens from

``oidc_client_id`` - OIDC client ID to request credentials

``oidc_client_secret`` - OIDC client "secret" to request credentials

``oidc_scopes`` - A list of scopes required for OIDC client

Files
=====

:file:`/usr/share/doc/waiverdb/client.conf.example`

    Template for configuration file.

Example
=======

.. include:: ../conf/client.conf.example
   :literal:
