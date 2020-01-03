# WaiverDB

![logo of WaiverDB](https://pagure.io/waiverdb/raw/master/f/logo.png)

## What is WaiverDB

WaiverDB is a companion service to
[ResultsDB](https://pagure.io/taskotron/resultsdb), for recording waivers
against test results.

## Quick development setup

The fastest way to setting up development environment is to install
docker-compose or podman-compose and use `make up` to provision required
containers and use `make test` to run tests or `make coverage` to generate and
open coverage report.

As alternative to using containers, below are steps to set up development
environment on local machine.

Install dependencies:

    $ sudo dnf builddep waiverdb.spec

Configure Postgres on the local machine, with a `waiverdb` database:

    $ sudo dnf install postgresql-server
    $ sudo postgresql-setup --initdb
    $ sudo systemctl enable --now postgresql
    $ sudo -u postgres createuser --superuser $USER
    $ createdb waiverdb

Create a local configuration file:

    $ cp conf/settings.py.example conf/settings.py

Populate the database:

    $ PYTHONPATH=. DEV=true python3 waiverdb/manage.py db upgrade

Run the server:

    $ PYTHONPATH=. DEV=true python3 waiverdb/manage.py run -h localhost -p 5004 --debugger

The server is now running at <http://localhost:5004> and API calls can be sent to
<http://localhost:5004/api/v1.0>. All data is stored in the `waiverdb` Postgres 
database on the local machine. You can verify the server is running correctly 
by visiting <http://localhost:5004/api/v1.0/about>.


## Adjusting configuration

You can configure this app by copying `conf/settings.py.example` into
`conf/settings.py` and adjusting values as you see fit. It overrides default
values in `waiverdb/config.py`.

## Running test suite

You can run this test suite with the following command::

    $ py.test-3 tests/

The test suite will drop and re-create a Postgres database named 
`waiverdb_test`. By default, it expects to have superuser access to Postgres on 
the local machine.

To test against all supported versions of Python, you can use tox::

    $ sudo dnf install python3-tox
    $ tox

## Building the docs

You can view the docs locally with::

    $ cd docs
    $ make html
    $ firefox _build/html/index.html

## Viewing published fedmsgs

You can view fedmsgs published when new waivers get created by doing::

    $ fedmsg-relay --config-filename fedmsg.d/config.py &
    $ fedmsg-tail --config fedmsg.d/config.py --no-validate --really-pretty

### WaiverDB CLI
WaiverDB has a command-line client interface for creating new waivers against test
results. A sample configuration is installed as ``/usr/share/doc/waiverdb/client.conf.example``.
Copy it to ``/etc/waiverdb/client.conf`` and edit it there. Or you can use ``--config-file``
to specify one.
```
Usage: waiverdb-cli [OPTIONS]

  Creates new waivers against test results.

  Examples:

      waiverdb-cli -r 47 -r 48 -p "fedora-28" -c "This is fine"
or

      waiverdb-cli -t dist.rpmdeplint -s '{"item": "qclib-1.3.1-3.fc28", "type": "koji_build"}' -p "fedora-28" -c "This is expected for non-x86 packages"


Options:
  -C, --config-file PATH           Specify a config file to use.
  -r, --result-id INTEGER          Specify one or more results to be waived.
  -s, --subject TEXT               Deprecated. Use --subject-identifier and
                                   --subject-type instead. Subject for a result to waive.
  -i, --subject-identifier TEXT    Subject identifier for a result to waive.
  -T, --subject-type TEXT          Subject type for a result to waive.
  -t, --testcase TEXT              Specify a testcase for the subject.
  -p, --product-version TEXT       Specify one of PDC's product version
                                   identifiers.
  --waived / --no-waived           Whether or not the result is waived.
  -c, --comment TEXT               A comment explaining why the result is waived.
  -h, --help                       Show this message and exit.
```
