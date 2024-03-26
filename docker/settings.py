import os

DATABASE_URI = 'postgresql+psycopg2://waiverdb:waiverdb@waiverdb-db:5433/waiverdb'

if os.getenv('TEST') == 'true':
    DATABASE_URI += '_test'

HOST = '0.0.0.0'
PORT = 5004
AUTH_METHOD = 'dummy'
MESSAGE_BUS_PUBLISH = False
SUPERUSERS = ['dummy']
RESULTSDB_API_URL = 'http://resultsdb:5001/api/v2.0'

AUTH_METHODS = ['OIDC']
OIDC_CLIENT_SECRETS = '/etc/secret/client_secrets.json'

# use http OIDC callback URI
OIDC_OVERWRITE_REDIRECT_URI = 'http://127.0.0.1:5004/oidc_callback'
OIDC_CALLBACK_ROUTE = None

PERMANENT_SESSION_LIFETIME = 300
SESSION_COOKIE_NAME = "session"
SESSION_COOKIE_SAMESITE = "Lax"

PERMISSIONS = [
    {
        "name": "WaiverDB Admins",
        "testcases": ["test*"],
        "users": ["admin", "service-account-waiverdb"],
    },
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'loggers': {
        'waiverdb': {
            'level': 'DEBUG',
        },
        'flask-oidc': {
            'level': 'DEBUG',
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
            'format': '[%(levelname)s] %(name)s: %(message)s',
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console'],
    },
}
