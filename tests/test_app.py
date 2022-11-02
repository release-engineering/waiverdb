# SPDX-License-Identifier: GPL-2.0+

"""This module contains tests for :mod:`waiverdb.app`."""
from __future__ import unicode_literals

from mock import ANY, call, patch

from waiverdb import app, config
from flask_sqlalchemy import SignallingSession


class DisabledMessagingConfig(config.Config):
    MESSAGE_BUS_PUBLISH = False
    AUTH_METHOD = None
    SQLALCHEMY_TRACK_MODIFICATIONS = True


class EnabledMessagedConfig(config.Config):
    MESSAGE_BUS_PUBLISH = True
    AUTH_METHOD = None
    SQLALCHEMY_TRACK_MODIFICATIONS = True


@patch("waiverdb.app.event.listen")
def test_disabled_messaging_should_not_register_events(mock_listen):
    app.create_app(DisabledMessagingConfig)
    calls = [
        c for c in mock_listen.mock_calls if c == call(ANY, ANY, app.publish_new_waiver)
    ]
    assert calls == []


@patch("waiverdb.app.event.listen")
def test_enabled_messaging_should_register_events(mock_listen):
    app.create_app(EnabledMessagedConfig)
    calls = [
        c for c in mock_listen.mock_calls if c == call(ANY, ANY, app.publish_new_waiver)
    ]
    assert calls == [call(SignallingSession, "after_commit", app.publish_new_waiver)]
