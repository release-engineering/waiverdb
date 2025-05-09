# SPDX-License-Identifier: GPL-2.0+

"""This module contains tests for :mod:`waiverdb.app`."""
from __future__ import unicode_literals

from mock import ANY, call, patch

from waiverdb import app, config
from waiverdb.models import db
import sqlalchemy


class DisabledMessagingConfig(config.Config):
    SESSION_SQLALCHEMY_TABLE = "sessions-disabled-messaging"
    DATABASE_URI = 'sqlite:///:memory:'
    MESSAGE_BUS_PUBLISH = False
    AUTH_METHOD = None
    SQLALCHEMY_TRACK_MODIFICATIONS = True


class EnabledMessagedConfig(config.Config):
    SESSION_SQLALCHEMY_TABLE = "sessions-enabled-messaging"
    DATABASE_URI = 'sqlite:///:memory:'
    MESSAGE_BUS_PUBLISH = True
    AUTH_METHOD = None
    SQLALCHEMY_TRACK_MODIFICATIONS = True


@patch("waiverdb.app.sqlalchemy.event.listen")
def test_disabled_messaging_should_not_register_events(mock_listen):
    app.create_app(DisabledMessagingConfig)
    calls = [
        c for c in mock_listen.mock_calls if c == call(ANY, ANY, app.publish_new_waiver)
    ]
    assert calls == []


@patch("waiverdb.app.sqlalchemy.event.listen")
def test_enabled_messaging_should_register_events(mock_listen):
    app.create_app(EnabledMessagedConfig)
    calls = [
        c for c in mock_listen.mock_calls if c == call(ANY, ANY, app.publish_new_waiver)
    ]
    assert calls == [call(db.session, "after_commit", app.publish_new_waiver)]


def test_sqlalchemy_version():
    """
    Tests whether SQLAlchemy version is 2
    :return:
    """
    assert sqlalchemy.__version__.startswith('2')
