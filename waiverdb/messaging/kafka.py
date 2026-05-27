# SPDX-License-Identifier: GPL-2.0+

import json
import logging
import os
from typing import Any

from confluent_kafka import KafkaError, KafkaException, Message, Producer
from flask_restx import marshal
from pydantic import BaseModel
from sqlalchemy.orm import Session

import waiverdb.monitor as monitor
from waiverdb.fields import waiver_fields
from waiverdb.models import Waiver

_log = logging.getLogger(__name__)


class KafkaConfig(BaseModel):
    topic: str
    producer: dict[str, Any]
    flush_timeout_seconds: float = 20.0


def _parse_config(config) -> tuple[KafkaConfig, dict[str, Any]]:
    config_dict = config.get("KAFKA")
    if not isinstance(config_dict, dict):
        raise RuntimeError(
            f"KAFKA configuration is invalid, expected a dict, got: {config_dict!r}"
        )

    try:
        kafka_config = KafkaConfig(**config_dict)
    except (ValueError, TypeError) as e:
        raise RuntimeError(f"Invalid KAFKA configuration: {e}") from e

    username = os.environ.get("WAIVERDB_KAFKA_SASL_USERNAME")
    password = os.environ.get("WAIVERDB_KAFKA_SASL_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "WAIVERDB_KAFKA_SASL_USERNAME and WAIVERDB_KAFKA_SASL_PASSWORD "
            "environment variables are required"
        )
    producer_config = {
        **kafka_config.producer,
        "sasl.username": username,
        "sasl.password": password,
    }

    return kafka_config, producer_config


class KafkaPublisher:
    def __init__(self, config) -> None:
        kafka_config, producer_config = _parse_config(config)
        self._config = kafka_config
        self._producer = Producer(producer_config)

    def publish_new_waiver(self, session: Session) -> None:
        delivery_error = None

        def _delivery_callback(err: KafkaError | None, _msg: Message) -> None:
            nonlocal delivery_error
            if err is not None:
                _log.error("Failed to deliver Kafka message: %s", err)
                monitor.messaging_tx_failed_counter.inc()
                if delivery_error is None:
                    delivery_error = KafkaException(err)
            else:
                monitor.messaging_tx_sent_ok_counter.inc()

        for row in session.identity_map.values():
            if not isinstance(row, Waiver):
                continue
            monitor.messaging_tx_to_send_counter.inc()
            _log.debug("Publishing a Kafka message for %r", row)
            message_data = marshal(row, waiver_fields)
            self._producer.produce(
                self._config.topic,
                value=json.dumps(message_data).encode("utf-8"),
                on_delivery=_delivery_callback,
            )

        remaining = self._producer.flush(timeout=self._config.flush_timeout_seconds)
        if remaining > 0:
            _log.error(
                "%d Kafka message(s) failed to be delivered (timeout)", remaining
            )
            monitor.messaging_tx_failed_counter.inc()
            raise KafkaException(
                KafkaError(
                    KafkaError._MSG_TIMED_OUT,
                    f"{remaining} message(s) were not delivered within timeout",
                )
            )

        if delivery_error is not None:
            raise delivery_error
