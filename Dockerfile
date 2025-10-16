# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV DJANGO_SETTINGS_MODULE=adminstudio_django.settings.prod \
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

# Collect static files (harmless if not configured)
RUN DJANGO_ENV=prod python manage.py collectstatic --noinput || true

EXPOSE 80

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn adminstudio_django.wsgi:application --bind 0.0.0.0:80 --workers 3 --threads 2 --timeout 120"]