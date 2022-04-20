# SPDX-License-Identifier: GPL-2.0+

from fedora_messaging import message


SCHEMA_URL = "http://fedoraproject.org/message-schema/"

WAIVERDB_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "comment": {"type": "string"},
        "username": {"type": "string", "format": "uri"},
        "waived": {"type": "boolean"},
        "timestamp": {"type": "string"},
        "product_version": {"type": "string"},
        "testcase": {"type": "string"},
        "proxied_by": {"type": ["string", "null"]},
        "id": {"type": "number"},
        "scenario": {"type": ["string", "null"]},
        "subject_identifier": {"type": "string"},
        "subject_type": {"type": "string"},
    },
    "required": [
        "waived",
        "username",
        "product_version",
        "subject_identifier",
        "subject_type",
        "scenario",
        "testcase",
    ],
}


class WaiverDBMessage(message.Message):
    """
    A sub-class of a Fedora message that defines a message schema for messages
    published by waiverdb.
    """

    @property
    def app_name(self):
        return "waiverdb"

    @property
    def app_icon(self):
        return "https://github.com/release-engineering/waiverdb/logo.png"

    @property
    def username(self):
        return self.body.get("body").get("username")

    @property
    def testcase(self):
        return self.body.get("body").get("testcase")
