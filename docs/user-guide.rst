.. _user-guide:

==========
User Guide
==========

WaiverDB is service allowing to waive test results from `ResultsDB`_.

You can use :ref:`rest-api` to modify and query waived states. To simplify
making requests, use ``waiverdb-cli``.

waiverdb-cli
============

``waiverdb-cli`` is command-line tool for modifying and querying waived
states stored in WaiverDB server.

Use ``--help`` to see common usage. For more details refer to
:ref:`waiverdb-cli(1) <waiverdb-cli>` manual page (``man 1 waiverdb-cli``).

Examples
--------

Waive test results with IDs 47 and 48 and specific product version::

    waiverdb-cli -r 47 -r 48 -p "fedora-28" -c "This is fine"

Waive test results with specific subject and product version::

    waiverdb-cli -t dist.rpmdeplint \
        -s '{"item": "qclib-1.3.1-3.fc28", "type": "koji_build"}' \
        -p "fedora-28" -c "This is expected for non-x86 packages"

Installation
------------

Either install system package, e.g. on Fedora::

    $ sudo dnf install waiverdb-cli

or install ``waiverdb`` PyPI package::

    $ pip install --user waiverdb

.. _ResultsDB: https://pagure.io/taskotron/resultsdb

Configuration
-------------

The tool reads a configuration file to know which server and authentication
method to use.

Default configuration is taken from :file:`/etc/waiverdb/client.conf`. You can
use ``--config-file`` flag to specify different one.

For more details about the configuration file refer to
:ref:`waiverdb-client.conf(5) <client-conf>` manual page (``man 5
waiverdb-client.conf``).
