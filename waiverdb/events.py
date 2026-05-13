# SPDX-License-Identifier: GPL-2.0+
"""
This module contains a set of `SQLAlchemy event`_ hooks.

To use these hooks, you must register them with SQLAlchemy
using the :func:`sqlalchemy.event.listen` function.

.. _SQLALchemy events:
    https://docs.sqlalchemy.org/en/latest/orm/events.html
"""

import logging

from flask import current_app

_log = logging.getLogger(__name__)


def publish_new_waiver(session):
    """
    A post-commit event hook that emits messages to a message bus.

    This event is designed to be registered with a session factory::

        >>> from sqlalchemy.event import listen
        >>> listen(MyScopedSession, 'after_commit', publish_new_waiver)

    Args:
        session (sqlalchemy.orm.Session): The session that was committed to the
            database. This session is not active and cannot emit SQL.

    """
    _log.debug(
        "The publish_new_waiver SQLAlchemy event has been activated (%r)",
        current_app.config["MESSAGE_PUBLISHER"],
    )
    current_app.publisher.publish_new_waiver(session)
