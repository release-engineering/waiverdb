# SPDX-License-Identifier: GPL-2.0+

import os
from mock import patch
import pytest
from waiverdb.app import create_app
from waiverdb.models import db


@pytest.fixture(scope='session')
def app():
    os.environ['TEST'] = 'true'
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def session(monkeypatch):
    """Patch Flask-SQLAlchemy to use a specific connection"""
    db.drop_all()
    db.create_all()
    with db.engine.connect() as connection:
        # Patch Flask-SQLAlchemy to use our connection
        monkeypatch.setattr(db, 'get_engine', lambda *args: connection)

        yield db.session

        db.session.remove()


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
