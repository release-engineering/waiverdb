# SPDX-License-Identifier: GPL-2.0+

import os


class Config(object):
    """
    A WaiverDB Flask configuration.
    """
    DEBUG = True
    DATABASE_URI = 'postgresql+psycopg2:///waiverdb'
    HOST = '127.0.0.1'
    PORT = 5004
    PRODUCTION = False
    SHOW_DB_URI = False
    SECRET_KEY = 'replace-me-with-something-random'  # nosec

    RESULTSDB_API_URL = 'https://taskotron.fedoraproject.org/resultsdb_api/api/v2.0'

    # Disable 404 error message with suggestions of other endpoints that
    # closely match the requested endpoint.
    RESTX_ERROR_404_HELP = False

    FLASK_PYDANTIC_VALIDATION_ERROR_RAISE = True

    AUTH_METHOD = 'OIDC'  # Specify OIDC, Kerberos or SSL for authentication
    OIDC_SCOPES = 'openid'
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
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT = None
    OTEL_EXPORTER_SERVICE_NAME = "waiverdb"

    # Secure cookies
    PERMANENT_SESSION_LIFETIME = 300
    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Call error handlers
    PROPAGATE_EXCEPTIONS = True

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'loggers': {
            'waiverdb': {
                'level': 'INFO',
            },
            # Skip printing tracebacks on frequent tracing connection issues
            'opentelemetry.sdk.trace.export': {
                'level': 'CRITICAL',
            },
        },
        'handlers': {
            'console': {
                'formatter': 'bare',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'level': 'DEBUG',
            },
        },
        'formatters': {
            'bare': {
                # Drop timestamp and process ID, already included in Apache logs
                'format': '[%(levelname)s] %(name)s: %(message)s',
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console'],
        },
    }


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
    OIDC_RESOURCE_SERVER_ONLY = True
    SUPERUSERS = ['bodhi']

    CORS_ORIGINS = 'https://bodhi.fedoraproject.org'
