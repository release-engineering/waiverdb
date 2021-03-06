# SPDX-License-Identifier: GPL-2.0+

import os
from mock import patch
import pytest
from waiverdb.app import create_app
from waiverdb.models import db as waiverdb_db


@pytest.fixture(scope='session')
def app():
    os.environ['TEST'] = 'true'
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture(scope='session')
def db(app):
    """Session-wide test database."""
    waiverdb_db.create_all()
    return waiverdb_db


@pytest.fixture
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


@pytest.fixture
def client(app):
    """A Flask test client. An instance of :class:`flask.testing.TestClient`
    by default.
    """
    with app.test_client() as client:
        with patch('waiverdb.events.publish'):
            yield client


@pytest.fixture()
def enable_kerberos(app, monkeypatch):
    monkeypatch.setitem(app.config, 'AUTH_METHOD', 'Kerberos')


@pytest.fixture()
def enable_ssl(app, monkeypatch):
    monkeypatch.setitem(app.config, 'AUTH_METHOD', 'SSL')


@pytest.fixture()
def enable_ldap_host(app, monkeypatch):
    monkeypatch.setitem(app.config, 'LDAP_HOST', 'ldap://ldap.something.com')


@pytest.fixture()
def enable_ldap_base(app, monkeypatch):
    monkeypatch.setitem(app.config, 'LDAP_BASE', 'ou=Users,dc=something,dc=com')
