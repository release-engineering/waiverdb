# SPDX-License-Identifier: GPL-2.0+

import logging

import waiverdb.monitor as monitor

_log = logging.getLogger(__name__)


class NullPublisher:
    def publish_new_waiver(self, session):
        _log.info("No message published. MESSAGE_PUBLISHER disabled.")
        monitor.messaging_tx_stopped_counter.inc()


def create_publisher(config):
    publisher_type = config.get("MESSAGE_PUBLISHER")

    if publisher_type == "kafka":
        from waiverdb.messaging.kafka import KafkaPublisher

        return KafkaPublisher(config)

    if publisher_type == "stomp":
        from waiverdb.messaging.stomp import StompPublisher

        return StompPublisher(config)

    if publisher_type == "fedmsg":
        from waiverdb.messaging.fedmsg import FedmsgPublisher

        return FedmsgPublisher()

    if publisher_type is None:
        return NullPublisher()

    raise RuntimeError(f"Unknown MESSAGE_PUBLISHER: {publisher_type!r}")
