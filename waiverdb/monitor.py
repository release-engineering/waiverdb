# SPDX-License-Identifier: GPL-2.0+

# For an up-to-date version of this module, see:
#   https://pagure.io/monitor-flask-sqlalchemy

# pylint: disable=W,unexpected-keyword-arg,no-value-for-parameter

import os
import tempfile

from flask import Response
from flask.views import MethodView
from prometheus_client import (  # noqa: F401
    ProcessCollector, CollectorRegistry, Counter, multiprocess,
    Histogram, generate_latest, start_http_server, CONTENT_TYPE_LATEST)
from sqlalchemy import event

# Service-specific imports


if not os.environ.get('prometheus_multiproc_dir'):
    os.environ.setdefault('prometheus_multiproc_dir', tempfile.mkdtemp())
registry = CollectorRegistry()
ProcessCollector(registry=registry)
multiprocess.MultiProcessCollector(registry)
if os.getenv('MONITOR_STANDALONE_METRICS_SERVER_ENABLE', 'false') == 'true':
    port = os.getenv('MONITOR_STANDALONE_METRICS_SERVER_PORT', '10040')
    start_http_server(int(port), registry=registry)


# Generic metrics
messaging_tx_to_send_counter = Counter(
    'messaging_tx_to_send',
    'Total number of messages to send',
    registry=registry)
messaging_tx_stopped_counter = Counter(
    'messaging_tx_stopped',
    'Number of messages, which were eventually stopped before sending',
    registry=registry)
messaging_tx_sent_ok_counter = Counter(
    'messaging_tx_sent_ok',
    'Number of messages, which were sent successfully',
    registry=registry)
messaging_tx_failed_counter = Counter(
    'messaging_tx_failed',
    'Number of messages, for which the sender failed',
    registry=registry)

db_dbapi_error_counter = Counter(
    'db_dbapi_error',
    'Number of DBAPI errors',
    registry=registry)
db_engine_connect_counter = Counter(
    'db_engine_connect',
    'Number of \'engine_connect\' events',
    registry=registry)
db_handle_error_counter = Counter(
    'db_handle_error',
    'Number of exceptions during connection',
    registry=registry)
db_transaction_rollback_counter = Counter(
    'db_transaction_rollback',
    'Number of transactions, which were rolled back',
    registry=registry)

# Service-specific metrics
# XXX: TODO


def db_hook_event_listeners(target=None):
    # Service-specific import of db
    from waiverdb.models import db

    if not target:
        target = db.engine

    @event.listens_for(target, 'dbapi_error', named=True)
    def receive_dbapi_error(**kw):
        db_dbapi_error_counter.inc()

    @event.listens_for(target, 'engine_connect')
    def receive_engine_connect(conn, branch):
        db_engine_connect_counter.inc()

    @event.listens_for(target, 'handle_error')
    def receive_handle_error(exception_context):
        db_handle_error_counter.inc()

    @event.listens_for(target, 'rollback')
    def receive_rollback(conn):
        db_transaction_rollback_counter.inc()


class MonitorAPI(MethodView):
    def get(self):
        return Response(generate_latest(registry),
                        content_type=CONTENT_TYPE_LATEST)
