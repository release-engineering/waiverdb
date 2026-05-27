# SPDX-License-Identifier: GPL-2.0+

import json
import logging
import time
from contextlib import contextmanager

import stomp
from flask_restx import marshal
from sqlalchemy.orm import Session

import waiverdb.monitor as monitor
from waiverdb.fields import waiver_fields
from waiverdb.models import Waiver

_log = logging.getLogger(__name__)

MAX_STOMP_RETRY = 3
STOMP_RETRY_DELAY_SECONDS = 5


@contextmanager
def _stomp_connection(configs):
    conn_args = configs["connection"].copy()
    if "use_ssl" in conn_args:
        use_ssl = conn_args.pop("use_ssl")
    else:
        use_ssl = False

    ssl_args = {"for_hosts": conn_args["host_and_ports"]}
    for attr in ("key_file", "cert_file", "ca_certs"):
        conn_attr = f"ssl_{attr}"
        if conn_attr in conn_args:
            ssl_args[attr] = conn_args.pop(conn_attr)

    conn = stomp.connect.StompConnection11(**conn_args)

    if use_ssl:
        conn.set_ssl(**ssl_args)

    conn.connect(wait=True, **configs.get("credentials", {}))

    try:
        yield conn
    finally:
        conn.disconnect()


class StompPublisher:
    def __init__(self, config) -> None:
        configs = config.get("STOMP_CONFIGS")
        if not configs:
            raise RuntimeError(
                "stomp was configured to publish messages, "
                "but STOMP_CONFIGS is not configured"
            )
        if "destination" not in configs or not configs["destination"]:
            raise RuntimeError(
                "stomp was configured to publish messages, "
                "but destination is not configured in STOMP_CONFIGS"
            )
        if "connection" not in configs or not configs["connection"]:
            raise RuntimeError(
                "stomp was configured to publish messages, "
                "but connection is not configured in STOMP_CONFIGS"
            )
        self._configs = configs
        self._max_retry = config.get("MAX_STOMP_RETRY", MAX_STOMP_RETRY)
        self._retry_delay = config.get(
            "STOMP_RETRY_DELAY_SECONDS", STOMP_RETRY_DELAY_SECONDS
        )

    def publish_new_waiver(self, session: Session) -> None:
        for i in range(self._max_retry):
            time.sleep(i * self._retry_delay)
            try:
                self._send(session)
            except stomp.exception.StompException:
                _log.exception(
                    "Failed to send message (try %s/%s)", i + 1, self._max_retry
                )
            else:
                break

    def _send(self, session: Session) -> None:
        with _stomp_connection(self._configs) as conn:
            for row in session.identity_map.values():
                monitor.messaging_tx_to_send_counter.inc()
                if not isinstance(row, Waiver):
                    continue
                _log.debug("Publishing a message for %r", row)
                msg = json.dumps(marshal(row, waiver_fields))
                kwargs = dict(
                    body=msg,
                    headers={},
                    destination=self._configs["destination"],
                )
                try:
                    conn.send(**kwargs)
                    monitor.messaging_tx_sent_ok_counter.inc()
                except Exception:
                    _log.exception("Couldn't publish message via stomp")
                    monitor.messaging_tx_failed_counter.inc()
                    raise
