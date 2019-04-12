# SPDX-License-Identifier: GPL-2.0+

import os
from copy import copy
from mock import patch
import pytest
from sqlalchemy import create_engine
from waiverdb.app import create_app
from waiverdb.monitor import db_hook_event_listeners


@pytest.fixture(scope='session')
def app(request):
    os.environ['TEST'] = 'true'
    app = create_app()
    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app


@pytest.fixture(scope='session')
def db(app):
    """Session-wide test database."""
    from waiverdb.models import db
    dbname = db.engine.url.database
    # In order to drop and re-create the database, we have to connect to
    # template1 database in special AUTOCOMMIT isolation level.
    dburl = copy(db.engine.url)
    dburl.database = 'template1'
    with create_engine(dburl).connect() as connection:
        connection.execution_options(isolation_level='AUTOCOMMIT')
        connection.execute('DROP DATABASE IF EXISTS {}'.format(dbname))
        connection.execute('CREATE DATABASE {}'.format(dbname))
    db.create_all()
    db_hook_event_listeners()
    return db


@pytest.yield_fixture
def session(db, monkeypatch):
    """Patch Flask-SQLAlchemy to use a specific connection"""
    connection = db.engine.connect()
    transaction = connection.begin()

    # Patch Flask-SQLAlchemy to use our connection
    monkeypatch.setattr(db, 'get_engine', lambda *args: connection)

    yield db.session

    db.session.remove()
    transaction.rollback()
    connection.close()


@pytest.yield_fixture
def client(app):
    """A Flask test client. An instance of :class:`flask.testing.TestClient`
    by default.
    """
    with app.test_client() as client:
        with patch('fedora_messaging.api._session_cache'):
            yield client


@pytest.fixture()
def enable_kerberos(app, monkeypatch):
    monkeypatch.setitem(app.config, 'AUTH_METHOD', 'Kerberos')


@pytest.fixture()
def enable_ssl(app, monkeypatch):
    monkeypatch.setitem(app.config, 'AUTH_METHOD', 'SSL')


@pytest.fixture()
def enable_cors(app, monkeypatch):
    monkeypatch.setitem(app.config, 'CORS_URL', 'https://bodhi.fedoraproject.org')


@pytest.fixture()
def enable_permission_mapping(app, monkeypatch):
    monkeypatch.setitem(app.config, 'PERMISSION_MAPPING',
                        {
                            "^testcase1.*": {"groups": ["factory-2-0"], "users": []}, # noqa
                            "^testcase2.*": {"groups": [], "users": ["foo"]}, # noqa
                            "^testcase4.*": {"groups": [], "users": []} # noqa
                        })


@pytest.fixture()
def enable_ldap_host(app, monkeypatch):
    monkeypatch.setitem(app.config, 'LDAP_HOST', 'ldap://ldap.something.com')


@pytest.fixture()
def enable_ldap_base(app, monkeypatch):
    monkeypatch.setitem(app.config, 'LDAP_BASE', 'ou=Users,dc=something,dc=com')
