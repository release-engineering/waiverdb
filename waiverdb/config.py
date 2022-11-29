# SPDX-License-Identifier: GPL-2.0+

import os


class Config(object):
    """
    A WaiverDB Flask configuration.
    """
    DEBUG = True
    DATABASE_URI = 'postgresql+psycopg2:///waiverdb'
    # We configure logging explicitly, turn off the Flask-supplied log handler.
    LOGGER_HANDLER_POLICY = 'never'
    HOST = '127.0.0.1'
    PORT = 5004
    PRODUCTION = False
    SHOW_DB_URI = False
    SECRET_KEY = 'replace-me-with-something-random'  # nosec

    RESULTSDB_API_URL = 'https://taskotron.fedoraproject.org/resultsdb_api/api/v2.0'
    # need to explicitly turn this off
    # https://github.com/flask-restful/flask-restful/issues/449
    ERROR_404_HELP = False
    AUTH_METHOD = 'OIDC'  # Specify OIDC, Kerberos or SSL for authentication
    OIDC_USERNAME_FIELD = 'preferred_username'
    # Set this to True or False to enable publishing to a message bus
    MESSAGE_BUS_PUBLISH = True
    # Specify fedmsg or stomp for publishing messages
    MESSAGE_PUBLISHER = 'fedmsg'
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    # A list of users are allowed to create waivers on behalf of other users.
    SUPERUSERS = []
    PERMISSIONS = []
    # Deprecated permission mapping
    PERMISSION_MAPPING = {}


class ProductionConfig(Config):
    DEBUG = False
    PRODUCTION = True


class DevelopmentConfig(Config):
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    TRAP_BAD_REQUEST_ERRORS = True
    SHOW_DB_URI = True
    # The location of the client_secrets.json file used for API authentication
    OIDC_CLIENT_SECRETS = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'conf',
        'client_secrets.json'
    )
    OIDC_REQUIRED_SCOPE = 'https://waiverdb.fedoraproject.org/oidc/create-waiver'
    OIDC_RESOURCE_SERVER_ONLY = True


class TestingConfig(Config):
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    TRAP_BAD_REQUEST_ERRORS = True
    # Beware that the tests constantly wipe and re-create this database!
    # Do not configure this to point at any data you care about!
    DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    OIDC_CLIENT_SECRETS = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests',
        'client_secrets.json'
    )
    OIDC_REQUIRED_SCOPE = 'waiverdb_scope'
    OIDC_RESOURCE_SERVER_ONLY = True
    SUPERUSERS = ['bodhi']

    CORS_ORIGINS = 'https://bodhi.fedoraproject.org'
