# SPDX-License-Identifier: GPL-2.0+

import logging

from fedora_messaging.api import Message, publish
from fedora_messaging.exceptions import ConnectionException, PublishReturned
from flask_restx import marshal
from sqlalchemy.orm import Session

import waiverdb.monitor as monitor
from waiverdb.fields import waiver_fields
from waiverdb.models import Waiver

_log = logging.getLogger(__name__)


class FedmsgPublisher:
    def publish_new_waiver(self, session: Session) -> None:
        for row in session.identity_map.values():
            monitor.messaging_tx_to_send_counter.inc()
            if not isinstance(row, Waiver):
                continue
            _log.debug("Publishing a message for %r", row)
            try:
                msg = Message(
                    topic="waiverdb.waiver.new",
                    body=marshal(row, waiver_fields),
                )
                publish(msg)
                monitor.messaging_tx_sent_ok_counter.inc()
            except PublishReturned as e:
                _log.exception(
                    "Fedora Messaging broker rejected message %s: %s", msg.id, e
                )
                monitor.messaging_tx_failed_counter.inc()
            except ConnectionException as e:
                _log.exception("Error sending message %s: %s", msg.id, e)
                monitor.messaging_tx_failed_counter.inc()
                raise
