# SPDX-License-Identifier: GPL-2.0+

from .base import SCHEMA_URL, WaiverDBMessage, WAIVERDB_MESSAGE_SCHEMA


class WaiverDBMessageV1(WaiverDBMessage):
    """
    A sub-class of a Fedora message that defines a message schema for messages
    published by waiverdb when a waiverdb message is created.
    """

    topic = "org.fedoraproject.dev.waiverdb.waiver.new"

    body_schema = {
        "id": SCHEMA_URL + topic,
        "$schema": "http://json-schema.org/draft-04/schema#",
        "description": "Schema for waiverdb messages",
        "type": "object",
        "properties": {
            "queue": {"type": ["string", "null"]},
            "id": {"type": "string"},
            "topic": {"type": "string"},
            "headers": {"type": "object"},
            "body": WAIVERDB_MESSAGE_SCHEMA,
        },
        "required": ["id", "topic", "body", "headers"],
    }

    def __str__(self):
        """Return a complete human-readable representation of the message."""
        return (
            "WaiverDB message: Test case {testcase} is waived\nBy: {username}\n".format(
                testcase=self.body["body"]["testcase"],
                username=self.body["body"]["username"],
            )
        )

    @property
    def summary(self):
        """Return a summary of the message."""
        return '{username} created a waived message "{msg_id}"'.format(
            username=self.body["body"]["username"],
            msg_id=self.body["id"],
        )
