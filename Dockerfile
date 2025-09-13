# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
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

# Collect static files (harmless if not configured)
RUN python manage.py collectstatic --noinput || true

# Non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 80

CMD ["gunicorn", "adminstudio_django.wsgi:application", \
     "--bind", "0.0.0.0:80", \
     "--workers", "3", \
     "--threads", "2", \
     "--timeout", "120"]