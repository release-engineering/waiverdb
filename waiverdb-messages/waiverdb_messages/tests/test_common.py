# SPDX-License-Identifier: GPL-2.0+

"""Unit tests for common properties of the message schemas."""

from waiverdb_messages import WaiverDBMessageV1
from .utils import DUMMY_MSG


def test_properties():
    """Assert some properties are correct."""
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

    assert message.app_name == "waiverdb"
    assert (
        message.app_icon == "https://github.com/release-engineering/waiverdb/logo.png"
    )
    assert message.username == "packagerbot"
    assert message.testcase == "t.e.s.t.case"
