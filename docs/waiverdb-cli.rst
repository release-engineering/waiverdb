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

.. option:: -S, --scenario SCENARIO

    Specify a scenario for a result to waive.

.. option:: -p, --product-version TEXT

    Specify one of PDC's product version identifiers.

.. option:: --waived, --no-waived

    Whether or not the result is waived.

.. option:: -c, --comment TEXT

    A comment explaining why the result is waived.

.. option:: -u, --username TEXT

    Username on whose behalf the caller is proxying.

.. option:: -h, --help

    Print usage help and exit.

.. note::

    Usually, **subject_identifier** must match **item** result's data in ResultsDB.

    Usually, **subject_type** must match **type** in ResultsDB.

    And there is no restriction for **subject_type** and **subject_identifier**, so the basic info on
    how to figure out the identifier is as following:

    If the result is failed, user can check the value of **item** in ResultsDB:

    - *https://taskotron.fedoraproject.org/resultsdb_api/api/v2.0/results/{ID}*

    If the result is missing, they can get the value from previous waivers or results of the same **subject_type**/**type**:

    - *https://waiverdb.fedoraproject.org/api/v1.0/waivers/?subject_type={subject_type}*
    - *https://taskotron.fedoraproject.org/resultsdb_api/api/v2.0/results?type={subject_type}*

    If user does not even know the **type**, they can list all distinct types for the failed test case:

    - *https://taskotron.fedoraproject.org/resultsdb_api/api/v2.0/results/latest?_distinct_on=type&testcases={testcases}*


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

Waive test results with a specific subject and scenario::

    waiverdb-cli -t update.install_default_update_live \
        -i FEDORA-2020-a70501de3d -T koji_build \
        -S "fedora.updates-everything-boot-iso.x86_64.uefi" \
        -c "This is ok"
