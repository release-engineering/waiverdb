# WaiverDB

![logo of WaiverDB](https://pagure.io/waiverdb/raw/master/f/logo.png)

## What is WaiverDB

WaiverDB is a companion service to
[ResultsDB](https://github.com/release-engineering/resultsdb), for recording waivers
against test results.

## Development setup

To set up local environment for development, see
[./docs/developer-guide.rst](https://pagure.io/waiverdb/raw/master/f/docs/developer-guide.rst).

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
