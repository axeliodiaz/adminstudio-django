#!/bin/sh
set -e

# Bind HTTP immediately so Render's deploy health check passes. Remote
# Postgres (DATABASE_URL / Supabase) migrate + fixture/seed can take minutes
# and must not block port 80.
(
  python manage.py migrate --noinput
  python manage.py ensure_superuser
  python manage.py load_versioned_fixtures || echo "load_versioned_fixtures failed; continuing with seeds"
  python manage.py seed_demo_catalog
  python manage.py seed_coach_demo
  python manage.py seed_dashboard_demo
) &

exec gunicorn adminstudio_django.wsgi:application \
  --bind 0.0.0.0:80 \
  --workers 2 \
  --threads 2 \
  --timeout 120
