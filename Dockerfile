# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt requirements.txt
COPY requirements/base.txt requirements/base.txt
COPY requirements/prod.txt requirements/prod.txt
RUN pip install --no-cache-dir -r requirements/prod.txt

# Copy project
COPY . .

# Collect static (if any) - no staticfiles app configured by default but harmless
# RUN python manage.py collectstatic --noinput

EXPOSE 80

CMD ["gunicorn", "adminstudio_django.wsgi:application", "--bind", "0.0.0.0:80"]
