#!/bin/bash
set -ex
python3 waiverdb/manage.py wait-for-db
python3 waiverdb/manage.py db upgrade
exec gunicorn \
  --reload \
  --workers=1 \
  --threads=2 \
  --bind=0.0.0.0:5004 \
  --access-logfile=- \
  --enable-stdio-inheritance \
  waiverdb.wsgi:app
