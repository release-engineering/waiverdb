# SPDX-License-Identifier: GPL-2.0+

import os

try:
    from urllib.parse import urlparse, urlunsplit
except ImportError:
    from urlparse import urlparse, urlunsplit

from flask import Flask, current_app
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.exc import ProgrammingError
import requests

from waiverdb.events import publish_new_waiver
from waiverdb.logger import init_logging
from waiverdb.api_v1 import api_v1
from waiverdb.models import db
from waiverdb.utils import json_error
from flask_oidc import OpenIDConnect
from werkzeug.exceptions import default_exceptions
from waiverdb.monitor import db_hook_event_listeners


def enable_cors(app):
    """
    Enables CORS headers.
    """
    # backward compatibility with old CORS_URL option
    cors_url = app.config.get('CORS_URL')
    if cors_url:
        app.config['CORS_ORIGINS'] = cors_url

    CORS(app)


def load_config(app):
    # Load default config, then override that with a config file
    if os.getenv('DEV') == 'true':
        default_config_obj = 'waiverdb.config.DevelopmentConfig'
        default_config_file = os.getcwd() + '/conf/settings.py'
        silent = True
    elif os.getenv('TEST') == 'true':
        default_config_obj = 'waiverdb.config.TestingConfig'
        default_config_file = os.getcwd() + '/conf/settings.py'
        silent = True
    elif os.getenv('DOCS') == 'true':
        default_config_obj = 'waiverdb.config.DevelopmentConfig'
        default_config_file = os.getcwd() + '/conf/settings.py'
        silent = True
    else:
        default_config_obj = 'waiverdb.config.ProductionConfig'
        default_config_file = '/etc/waiverdb/settings.py'
        silent = False

    app.config.from_object(default_config_obj)
    config_file = os.environ.get('WAIVERDB_CONFIG', default_config_file)
    app.config.from_pyfile(config_file, silent=silent)

    # Allow overriding only DATABASE_URI for tests.
    if os.getenv('TEST') == 'true':
        db_uri = app.config['DATABASE_URI']
        app.config.from_object(default_config_obj)
        app.config['DATABASE_URI'] = db_uri

    if os.environ.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.environ['SECRET_KEY']


def populate_db_config(app):
    # Take the application-level DATABASE_URI setting, plus (optionally)
    # a DATABASE_PASSWORD from the environment, and munge them together into
    # the SQLALCHEMY_DATABASE_URI setting which is obeyed by Flask-SQLAlchemy.
    dburi = app.config['DATABASE_URI']
    if os.environ.get('DATABASE_PASSWORD'):
        parsed = urlparse(dburi)
        netloc = '{}:{}@{}'.format(parsed.username,
                                   os.environ['DATABASE_PASSWORD'],
                                   parsed.hostname)
        if parsed.port:
            netloc += ':{}'.format(parsed.port)
        dburi = urlunsplit(
            (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    if app.config['SHOW_DB_URI']:
        app.logger.debug('using DBURI: %s', dburi)
    app.config['SQLALCHEMY_DATABASE_URI'] = dburi


# applicaiton factory http://flask.pocoo.org/docs/0.12/patterns/appfactories/
def create_app(config_obj=None):
    app = Flask(__name__)
    if config_obj:
        app.config.from_object(config_obj)
    else:
        load_config(app)
    if app.config['PRODUCTION'] and app.secret_key == 'replace-me-with-something-random':  # nosec
        raise Warning("You need to change the app.secret_key value for production")

    # register error handlers
    for code in default_exceptions.keys():
        app.register_error_handler(code, json_error)
    app.register_error_handler(requests.ConnectionError, json_error)
    app.register_error_handler(requests.Timeout, json_error)

    populate_db_config(app)
    if app.config['AUTH_METHOD'] == 'OIDC':
        app.oidc = OpenIDConnect(app)
    # initialize logging
    init_logging(app)
    # initialize db
    db.init_app(app)
    # initialize db migrations
    migrations_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                  'migrations')
    Migrate(app, db, directory=migrations_dir)
    # register blueprints
    app.register_blueprint(api_v1, url_prefix="/api/v1.0")
    app.add_url_rule('/healthcheck', view_func=healthcheck)
    register_event_handlers(app)

    # initialize DB event listeners from the monitor module
    app.before_first_request(db_hook_event_listeners)

    enable_cors(app)

    return app


def healthcheck():
    """
    Request handler for performing an application-level health check. This is
    not part of the published API, it is intended for use by OpenShift or other
    monitoring tools.

    Returns a 200 response if the application is alive and able to serve requests.
    """
    try:
        db.session.execute("SELECT 1 FROM waiver LIMIT 0").fetchall()
    except ProgrammingError:
        current_app.logger.exception('Healthcheck failed on DB query.')
        raise RuntimeError('Unable to communicate with database.')

    return ('Health check OK', 200, [('Content-Type', 'text/plain')])


def register_event_handlers(app):
    """
    Register SQLAlchemy event handlers with the application's session factory.

    Args:
        app (flask.Flask): The Flask object with the configured scoped session
            attached as the ``session`` attribute.
    """
    if app.config['MESSAGE_BUS_PUBLISH']:
        # A workaround for https://github.com/mitsuhiko/flask-sqlalchemy/pull/364
        # can be removed after python-flask-sqlalchemy is upgraded to 2.2
        from flask_sqlalchemy import SignallingSession
        event.listen(SignallingSession, 'after_commit', publish_new_waiver)
