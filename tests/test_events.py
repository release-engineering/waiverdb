# SPDX-License-Identifier: GPL-2.0+

"""This module contains tests for :mod:`waiverdb.events`."""
from __future__ import unicode_literals
import pytest
from unittest.mock import Mock, patch
from confluent_kafka import KafkaException
from fedora_messaging import api, testing
from flask_restx import marshal
from waiverdb.models import Waiver
from waiverdb.fields import waiver_fields
from waiverdb.messaging.publishers import NullPublisher


def test_publish_new_waiver_with_fedmsg(session):
    waiver = Waiver(
        subject_type='koji_build',
        subject_identifier='glibc-2.26-27.fc27',
        testcase='testcase1',
        username='jcline',
        product_version='something',
        waived=True,
        comment='This is a comment',
    )

    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    expected_msg = api.Message(
        topic='waiverdb.waiver.new',
        body=marshal(waiver, waiver_fields)
    )

    with testing.mock_sends(expected_msg):
        sesh.commit()


@pytest.fixture
def kafka_publisher(app, monkeypatch):
    kafka_configs = {
        'topic': 'eng.waiverdb.waiver.new',
        'producer': {
            'bootstrap.servers': 'localhost:9092',
            'client.id': 'waiverdb-test',
        },
        'flush_timeout_seconds': 10.0,
    }
    monkeypatch.setitem(app.config, 'KAFKA', kafka_configs)
    monkeypatch.setitem(app.config, 'MESSAGE_PUBLISHER', 'kafka')
    monkeypatch.setenv('WAIVERDB_KAFKA_SASL_USERNAME', 'alice')
    monkeypatch.setenv('WAIVERDB_KAFKA_SASL_PASSWORD', 'secret')

    with patch('waiverdb.messaging.kafka.Producer'):
        from waiverdb.messaging.kafka import KafkaPublisher
        publisher = KafkaPublisher(app.config)

    mock_producer = Mock()
    mock_producer.flush.return_value = 0
    publisher._producer = mock_producer
    monkeypatch.setattr(app, 'publisher', publisher)
    return mock_producer


def test_publish_new_waiver_with_kafka(session, kafka_publisher, make_waiver):
    waiver = make_waiver()
    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    with patch('waiverdb.messaging.kafka.monitor'):
        sesh.commit()

    kafka_publisher.produce.assert_called_once()
    kafka_publisher.flush.assert_called_once()


def test_publish_new_waiver_with_kafka_error(session, kafka_publisher, make_waiver):
    kafka_publisher.flush.return_value = 1
    waiver = make_waiver()
    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    with patch('waiverdb.messaging.kafka.monitor') as mock_monitor:
        with pytest.raises(KafkaException):
            sesh.commit()

    mock_monitor.messaging_tx_failed_counter.inc.assert_called()


def test_publish_new_waiver_with_disabled_publisher(session, app, monkeypatch, make_waiver):
    monkeypatch.setattr(app, 'publisher', NullPublisher())
    waiver = make_waiver()
    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    with patch('waiverdb.messaging.publishers.monitor') as mock_monitor:
        sesh.commit()

    mock_monitor.messaging_tx_stopped_counter.inc.assert_called_once()


def test_publish_new_waiver_with_fedmsg_for_proxy_user(session):
    waiver = Waiver(
        subject_type='koji_build',
        subject_identifier='glibc-2.26-27.fc27',
        testcase='testcase1',
        username='jcline',
        product_version='something',
        waived=True,
        comment='This is a comment',
        proxied_by='bodhi'
    )
    sesh = session()
    sesh.add(waiver)
    sesh.flush()

    expected_msg = api.Message(
        topic='waiverdb.waiver.new',
        body=marshal(waiver, waiver_fields)
    )
    with testing.mock_sends(expected_msg):
        sesh.commit()
