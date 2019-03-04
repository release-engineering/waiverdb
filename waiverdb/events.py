# SPDX-License-Identifier: GPL-2.0+
"""
This module contains a set of `SQLAlchemy event`_ hooks.

To use these hooks, you must register them with SQLAlchemy
using the :func:`sqlalchemy.event.listen` function.

.. _SQLALchemy events:
    https://docs.sqlalchemy.org/en/latest/orm/events.html
"""

import logging

from flask_restful import marshal
import stomp
import json
import waiverdb.monitor as monitor

from fedora_messaging.api import Message, publish
from fedora_messaging.exceptions import PublishReturned, ConnectionException
from flask import current_app
from waiverdb.fields import waiver_fields
from waiverdb.models import Waiver
from waiverdb.utils import stomp_connection

_log = logging.getLogger(__name__)


def publish_new_waiver(session):
    """
    A post-commit event hook that emits messages to a message bus. The messages
    can be published by either fedora-messaging or stomp.

    This event is designed to be registered with a session factory::

        >>> from sqlalchemy.event import listen
        >>> listen(MyScopedSession, 'after_commit', publish_new_waiver)

    The emitted message will look like::

        {
          "username": "jcline",
          "i": 4,
          "timestamp": 1489686124,
          "msg_id": "2017-80e46243-e6f5-46df-8dcd-4d17809eb298",
          "topic": "org.fedoraproject.dev.waiverdb.waiver.new",
          "msg": {
            "comment": "Because I said so",
            "username": "http://jcline.id.fedoraproject.org/",
            "waived": true,
            "timestamp": "2017-03-16T17:42:04.209638",
            "product_version": "Satellite 6.3",
            "subject": "{\"a.nice.example\": \"this-is-a-really-nice-example\"}",
            "testcase": "t.e.s.t.case",
            "proxied_by": null,
            "id": 15
          }
        }

    Args:
        session (sqlalchemy.orm.Session): The session that was committed to the
            database. This session is not active and cannot emit SQL.

    """
    _log.debug('The publish_new_waiver SQLAlchemy event has been activated (%r)',
               current_app.config['MESSAGE_PUBLISHER'])

    if current_app.config['MESSAGE_PUBLISHER'] == 'stomp':
        with stomp_connection() as conn:
            stomp_configs = current_app.config.get('STOMP_CONFIGS')
            for row in session.identity_map.values():
                monitor.messaging_tx_to_send_counter.inc()
                if not isinstance(row, Waiver):
                    continue
                _log.debug('Publishing a message for %r', row)
                msg = json.dumps(marshal(row, waiver_fields))
                kwargs = dict(body=msg, headers={}, destination=stomp_configs['destination'])
                if stomp.__version__[0] < 4:
                    kwargs['message'] = kwargs.pop('body')  # On EL7, different sig.
                try:
                    conn.send(**kwargs)
                    monitor.messaging_tx_sent_ok_counter.inc()
                except Exception:
                    _log.exception('Couldn\'t publish message via stomp')
                    monitor.messaging_tx_failed_counter.inc()
                    raise

    elif current_app.config['MESSAGE_PUBLISHER'] == 'fedmsg':
        for row in session.identity_map.values():
            monitor.messaging_tx_to_send_counter.inc()
            if not isinstance(row, Waiver):
                continue
            _log.debug('Publishing a message for %r', row)
            try:
                msg = Message(
                    topic='waiverdb.waiver.new',
                    body=marshal(row, waiver_fields)
                )
                publish(msg)
                monitor.messaging_tx_sent_ok_counter.inc()
            except PublishReturned as e:
                _log.exception('Fedora Messaging broker rejected message %s: %s', msg.id, e)
                monitor.messaging_tx_failed_counter.inc()
            except ConnectionException as e:
                _log.exception('Error sending message %s: %s', msg.id, e)
                monitor.messaging_tx_failed_counter.inc()
                raise

    elif current_app.config['MESSAGE_PUBLISHER'] is None:
        _log.info('No message published.  MESSAGE_PUBLISHER disabled.')
        monitor.messaging_tx_stopped_counter.inc()

    else:
        _log.warning('Unhandled MESSAGE_PUBLISHER %r', current_app.config['MESSAGE_PUBLISHER'])
        monitor.messaging_tx_failed_counter.inc()
