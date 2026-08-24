import os

import dj_database_url

from adminstudio_django.settings.base import *  # noqa

# Production overrides
DEBUG = False

# Serve collected static files (admin CSS/JS) from Gunicorn
MIDDLEWARE = [
    MIDDLEWARE[0],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]

# Ensure Browsable API is disabled (JSON only from base)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
]

# Hosts can be provided via env; keep the one already used plus sane defaults
ALLOWED_HOSTS += ["adminstudio-django.onrender.com"]  # from base; override via DJANGO_ALLOWED_HOSTS

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"

# Define a directory inside the container to collect static files
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Postgres (Supabase) via DATABASE_URL. SQLite on /data does not survive
# Render deploys without a disk and is not suitable for multi-instance prod.
_database_url = os.environ.get("DATABASE_URL", "").strip()
if not _database_url:
    raise RuntimeError(
        "DATABASE_URL is required in production. "
        "Use the Supabase Postgres URI with sslmode=require."
    )

DATABASES = {
    "default": dj_database_url.parse(
        _database_url,
        conn_max_age=60,
        conn_health_checks=True,
        ssl_require=True,
    )
}
