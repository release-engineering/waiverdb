# SPDX-License-Identifier: GPL-2.0+

import logging
import sys


def log_to_stdout(app, level=logging.INFO):
    fmt = '%(asctime)s [pid %(process)5d] %(name)s %(levelname)s %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    app.logger.addHandler(stream_handler)


def init_logging(app):
    log_level = logging.DEBUG if app.debug else logging.INFO
    log_to_stdout(app, level=log_level)
