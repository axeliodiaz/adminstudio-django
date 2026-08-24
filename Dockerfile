# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV DJANGO_SETTINGS_MODULE=adminstudio_django.settings.prod \
    DJANGO_ENV=prod \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (better caching)
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

# Copy project
COPY . .

# Create the path for the DB
RUN mkdir -p /data && chown -R 1000:1000 /data

# Collect static files for WhiteNoise / Gunicorn.
# prod settings require DATABASE_URL at import time; collectstatic does not
# open a connection, so a dummy URI is enough at build.
RUN DATABASE_URL=postgres://build:build@127.0.0.1:5432/postgres \
    DJANGO_ENV=prod python manage.py collectstatic --noinput

EXPOSE 80

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py ensure_superuser && python manage.py load_versioned_fixtures && python manage.py seed_demo_catalog && python manage.py seed_coach_demo && python manage.py seed_dashboard_demo && gunicorn adminstudio_django.wsgi:application --bind 0.0.0.0:80 --workers 3 --threads 2 --timeout 120"]
