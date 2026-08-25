#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py ensure_superuser

# Bind HTTP immediately so Render's deploy health check passes. Fixture
# loaddata is large (~200k reservations) and would otherwise time out boot.
(
  python manage.py load_versioned_fixtures
  python manage.py seed_demo_catalog
) &

exec gunicorn adminstudio_django.wsgi:application \
  --bind 0.0.0.0:80 \
  --workers 3 \
  --threads 2 \
  --timeout 120
