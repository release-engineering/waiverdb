=================
Development Guide
=================

Quick development setup
=======================

Clone `upstream git repository <https://pagure.io/waiverdb>`__::

    $ git clone https://github.com/release-engineering/waiverdb.git
    $ cd waiverdb

If you plan to fix issues or implement new features, create fork. Then update
"upstream" and "origin" remotes::

    $ git remote rename origin upstream
    $ git remote add origin git@github.com:$USER/waiverdb.git

Install packages required by pip to compile some python packages::

    $ sudo dnf install swig openssl-devel cpp gcc

Install dependencies in a virtual environment::

    $ poetry install

Run the server::

    $ cp conf/settings.py.example conf/settings.py
    $ DEV=true poetry run waiverdb run -h localhost -p 5004 --debugger

Migrate the db::

    $ DEV=true poetry run waiverdb db upgrade

The server is now running at on `localhost port 5004`_. Consult the
:ref:`rest-api` for available API calls. All data is stored inside
``/var/tmp/waiverdb_db.sqlite``.


Adjusting configuration
=======================

You can configure this app by copying ``conf/settings.py.example`` into
``conf/settings.py`` and adjusting values as you see fit. It overrides default
values in ``waiverdb/config.py``.


Running test suite
==================

To test against all supported versions of Python, you can use tox::

    $ sudo dnf install python3-tox
    $ tox

Building the documentation
==========================

You can build the documentation locally with ``tox -e docs`` or::

    $ cd docs
    $ make html

To view the documentation::

    $ firefox _build/html/index.html

.. _localhost port 5004: http://localhost:5004
