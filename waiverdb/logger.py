# SPDX-License-Identifier: GPL-2.0+

import logging
import sys


def log_to_stdout(level=logging.INFO):
    fmt = '%(asctime)s [pid %(process)5d] %(name)s %(levelname)s %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    logging.getLogger().addHandler(stream_handler)


def init_logging(app):
    log_level = logging.DEBUG if app.debug else logging.INFO
    log_to_stdout(level=log_level)
    # In general we want to see everything from our own code,
    # but not detailed debug messages from third-party libraries.
    # Note that the log level on the handler above controls what
    # will actually appear on stdout.
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger('waiverdb').setLevel(logging.DEBUG)
    # The SQLALCHEMY_ECHO setting comes from Flask-SQLAlchemy, which translates
    # it to echo=True in the call to create_engine(). But SQLAlchemy itself
    # warns not to do that if you are configuring Python logging correctly:
    # http://docs.sqlalchemy.org/en/latest/core/engines.html#configuring-logging
    # We intercept that setting and do it "properly" instead.
    if app.config.get('SQLALCHEMY_ECHO'):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        del app.config['SQLALCHEMY_ECHO']
