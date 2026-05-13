# SPDX-License-Identifier: GPL-2.0+

"""This module contains tests for :mod:`waiverdb.messaging.kafka`."""

import pytest
from unittest.mock import Mock, patch
from confluent_kafka import KafkaError, KafkaException

from waiverdb.messaging.kafka import KafkaPublisher


@pytest.fixture
def kafka_config(app, monkeypatch):
    config = {
        "topic": "eng.waiverdb.waiver.new",
        "producer": {
            "bootstrap.servers": "localhost:9092",
            "client.id": "waiverdb-test",
            "retries": 3,
        },
        "flush_timeout_seconds": 15.0,
    }
    monkeypatch.setitem(app.config, "KAFKA", config)
    monkeypatch.setenv("WAIVERDB_KAFKA_SASL_USERNAME", "alice")
    monkeypatch.setenv("WAIVERDB_KAFKA_SASL_PASSWORD", "secret")
    return config


@pytest.fixture
def kafka_publisher(app, kafka_config):
    with patch("waiverdb.messaging.kafka.Producer") as mock_producer_class:
        mock_producer = Mock()
        mock_producer.flush.return_value = 0
        mock_producer_class.return_value = mock_producer
        publisher = KafkaPublisher(app.config)
        yield publisher, mock_producer


def _simulate_successful_produce(mock_producer):
    """Make produce() invoke the on_delivery callback with no error on flush()."""
    callbacks = []

    def capture_produce(topic, value=None, on_delivery=None):
        callbacks.append(on_delivery)

    def trigger_flush(timeout=None):
        for cb in callbacks:
            if cb:
                cb(None, Mock())
        callbacks.clear()
        return 0

    mock_producer.produce.side_effect = capture_produce
    mock_producer.flush.side_effect = trigger_flush


def _simulate_failed_produce(mock_producer, error):
    """Make produce() invoke the on_delivery callback with an error on flush()."""
    callbacks = []

    def capture_produce(topic, value=None, on_delivery=None):
        callbacks.append(on_delivery)

    def trigger_flush(timeout=None):
        for cb in callbacks:
            if cb:
                cb(error, None)
        callbacks.clear()
        return 0

    mock_producer.produce.side_effect = capture_produce
    mock_producer.flush.side_effect = trigger_flush


def test_publish_success(session, kafka_publisher, make_waiver):
    publisher, mock_producer = kafka_publisher
    waiver = make_waiver()
    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    _simulate_successful_produce(mock_producer)

    with patch("waiverdb.messaging.kafka.monitor") as mock_monitor:
        publisher.publish_new_waiver(sesh)

    mock_producer.produce.assert_called_once()
    args, kwargs = mock_producer.produce.call_args
    assert args[0] == "eng.waiverdb.waiver.new"
    mock_producer.flush.assert_called_once_with(timeout=15.0)
    mock_monitor.messaging_tx_sent_ok_counter.inc.assert_called_once()


def test_publish_delivery_error(session, kafka_publisher, make_waiver):
    publisher, mock_producer = kafka_publisher
    waiver = make_waiver()
    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    mock_error = Mock()
    mock_error.__str__ = Mock(return_value="Connection failed")
    _simulate_failed_produce(mock_producer, mock_error)

    with patch("waiverdb.messaging.kafka.monitor") as mock_monitor:
        with pytest.raises(KafkaException):
            publisher.publish_new_waiver(sesh)

    mock_monitor.messaging_tx_to_send_counter.inc.assert_called_once()
    mock_monitor.messaging_tx_failed_counter.inc.assert_called_once()


def test_publish_flush_timeout(session, kafka_publisher, make_waiver):
    publisher, mock_producer = kafka_publisher
    waiver = make_waiver()
    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    mock_producer.flush.return_value = 1

    with patch("waiverdb.messaging.kafka.monitor") as mock_monitor:
        with pytest.raises(KafkaException) as exc_info:
            publisher.publish_new_waiver(sesh)

    err = exc_info.value.args[0]
    assert isinstance(err, KafkaError)
    assert err.code() == KafkaError._MSG_TIMED_OUT
    mock_monitor.messaging_tx_failed_counter.inc.assert_called()


def test_publish_multiple_waivers(session, kafka_publisher, make_waiver):
    publisher, mock_producer = kafka_publisher
    waiver1 = make_waiver(username="alice")
    waiver2 = make_waiver(
        username="bob", subject_identifier="gcc-7.3.1-5.fc28", testcase="testcase2")
    sesh = session()
    sesh.add(waiver1)
    sesh.add(waiver2)
    sesh.flush()

    _simulate_successful_produce(mock_producer)

    with patch("waiverdb.messaging.kafka.monitor") as mock_monitor:
        publisher.publish_new_waiver(sesh)

    assert mock_producer.produce.call_count == 2
    assert mock_monitor.messaging_tx_to_send_counter.inc.call_count == 2
    assert mock_monitor.messaging_tx_sent_ok_counter.inc.call_count == 2


def test_kafka_publisher_creation(app, kafka_config):
    with patch("waiverdb.messaging.kafka.Producer") as mock_producer_class:
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer

        publisher = KafkaPublisher(app.config)

        mock_producer_class.assert_called_once_with({
            "bootstrap.servers": "localhost:9092",
            "client.id": "waiverdb-test",
            "retries": 3,
            "sasl.username": "alice",
            "sasl.password": "secret",
        })
        assert publisher._config.topic == "eng.waiverdb.waiver.new"
        assert publisher._producer is mock_producer
