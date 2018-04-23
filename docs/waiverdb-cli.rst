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

``-C, --config-file PATH``

    Specify a config file to use.

``-r, --result-id INTEGER``

    Specify one or more results to be waived.

``-s, --subject TEXT``

    Specify one subject for a result to waive.

``-t, --testcase TEXT``

    Specify a testcase for the subject.

``-p, --product-version TEXT``

    Specify one of PDC's product version identifiers.

``--waived / --no-waived``

    Whether or not the result is waived.

``-c, --comment TEXT``

    A comment explaining why the result is waived.

``-h, --help``

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
