import os

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join("/data", "db.sqlite3"),
        "OPTIONS": {"timeout": 20},
    }
}
