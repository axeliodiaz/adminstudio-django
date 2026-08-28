import os

from adminstudio_django.settings.base import *  # noqa
from adminstudio_django.settings.database import production_databases

# Production overrides
DEBUG = False

# Ensure Browsable API is disabled (JSON only from base)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
]

# Hosts can be provided via env; keep the one already used plus sane defaults
ALLOWED_HOSTS += ["adminstudio-django.onrender.com"]  # from base; override via DJANGO_ALLOWED_HOSTS

INSTALLED_APPS += ["corsheaders"]
MIDDLEWARE = [
    MIDDLEWARE[0],
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]

_cors_extra = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
CORS_ALLOWED_ORIGINS = [
    "https://studio.axeldiaz.com",
    "https://www.studio.axeldiaz.com",
    "https://adminstudio-kohl.vercel.app",
    "https://adminstudio-axeldiaz.vercel.app",
    *_cors_extra,
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://adminstudio(-[\w]+)?-axeldiaz\.vercel\.app$",
    r"^https://adminstudio-[\w-]+\.vercel\.app$",
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)

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

# Production always uses Postgres. On Render, set DATABASE_URL to the
# Supabase session pooler (port 5432). migrate + fixtures run in render_start.sh.
DATABASES = production_databases()

EMAIL_DOMAIN = os.getenv("EMAIL_DOMAIN", "pulsefit.com")

# Links in emails (verify, wallet, reservations). Must not inherit the local Vite default.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://studio.axeldiaz.com")
