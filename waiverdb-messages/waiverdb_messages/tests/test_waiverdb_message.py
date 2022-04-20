# SPDX-License-Identifier: GPL-2.0+

"""Unit tests for the message schema."""

import pytest

from jsonschema import ValidationError
from ..waiverdb_message import WaiverDBMessageV1
from .utils import DUMMY_MSG


def test_required_fields():
    """
    Assert the message schema validates a message with the required fields.
    """
    body = {
        "headers": {
            "fedora_messaging_schema": "base.message",
            "fedora_messaging_severity": 20,
            "sent-at": "2022-04-26T03:58:37+00:00",
        },
        "topic": "dummy-topic",
        "id": "xxxyyy",
        "body": DUMMY_MSG,
    }
    message = WaiverDBMessageV1(body=body)
    message.validate()
    assert message.username == "packagerbot"


def test_missing_required_fields():
    """Assert an exception is actually raised on validation failure."""
    body = {
        "id": "xxxyyy",
        "body": DUMMY_MSG,
    }
    message = WaiverDBMessageV1(body=body)
    with pytest.raises(ValidationError):
        message.validate()


def test_str():
    """Assert __str__ produces a human-readable message."""
    body = {
        "headers": {
            "fedora_messaging_schema": "base.message",
            "fedora_messaging_severity": 20,
            "sent-at": "2022-04-26T03:58:37+00:00",
        },
        "topic": "dummy-topic",
        "id": "xxxyyy",
        "body": DUMMY_MSG,
    }

    expected_str = (
        "WaiverDB message: Test case t.e.s.t.case is waived\nBy: packagerbot\n"
    )
    message = WaiverDBMessageV1(body=body)
    message.validate()
    assert expected_str == str(message)


def test_summary():
    """Assert the summary is correct."""
    body = {
        "headers": {
            "fedora_messaging_schema": "base.message",
            "fedora_messaging_severity": 20,
            "sent-at": "2022-04-26T03:58:37+00:00",
        },
        "topic": "dummy-topic",
        "id": "xxxyyy",
        "body": DUMMY_MSG,
    }
    expected_summary = 'packagerbot created a waived message "xxxyyy"'
    message = WaiverDBMessageV1(body=body)
    assert expected_summary == message.summary
