import os

from adminstudio_django.settings.base import *  # noqa

# Production overrides
DEBUG = False

# Ensure Browsable API is disabled (JSON only from base)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
]

# Hosts can be provided via env; keep the one already used plus sane defaults
ALLOWED_HOSTS += ["3.86.184.243"]  # from base; override via DJANGO_ALLOWED_HOSTS

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"

# Define a directory inside the container to collect static files
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db" / "db.sqlite3",
}
