.. _waiverdb-cli:

============
waiverdb-cli
============

Synopsis
========

``waiverdb-cli [OPTIONS]``

Description
===========

**waiverdb-cli** is a CLI tool for reading and modifying WaiverDB (companion service to
ResultsDB, for recording waivers against).

Options
=======

.. option:: -C, --config-file PATH

    Specify a config file to use.

.. option:: -r, --result-id INTEGER

    Specify one or more results to be waived.

.. option:: -s, --subject TEXT

    Deprecated. Use --subject-identifier and --subject-type instead. Subject
    for a result to waive.

.. option:: -i, --subject-identifier TEXT

    Subject identifier for a result to waive.

.. option:: -T, --subject-type TEXT

    Subject type for a result to waive.

.. option:: -t, --testcase TEXT

    Specify a testcase for the subject.

.. option:: -p, --product-version TEXT

    Specify one of PDC's product version identifiers.

.. option:: --waived, --no-waived

    Whether or not the result is waived.

.. option:: -c, --comment TEXT

    A comment explaining why the result is waived.

.. option:: -h, --help

    Print usage help and exit.

Files
=====

:file:`/usr/share/doc/waiverdb/client.conf.example`

    Template for configuration file.

:file:`/etc/waiverdb/client.conf`

    Default configuration file.

Examples
========

Waive test results with IDs 47 and 48 and specific product version::

    waiverdb-cli -r 47 -r 48 -p "fedora-28" -c "This is fine"

Waive test results with specific subject and product version::

    waiverdb-cli -t dist.rpmdeplint \
        -s '{"item": "qclib-1.3.1-3.fc28", "type": "koji_build"}' \
        -p "fedora-28" -c "This is expected for non-x86 packages"
