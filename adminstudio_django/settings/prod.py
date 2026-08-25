import os

from adminstudio_django.settings.base import *  # noqa

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

# Postgres via DATABASE_URL when set (Supabase, Render Postgres, etc.).
# Render free often has no URL yet; sqlite on /data still lets boot finish
# and load versioned fixtures into the instance database.
_database_url = os.environ.get("DATABASE_URL", "").strip()
if _database_url:
    import dj_database_url

    _is_postgres = _database_url.lower().startswith(("postgres://", "postgresql://"))
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=0,
            conn_health_checks=True,
            ssl_require=_is_postgres and "sslmode=disable" not in _database_url.lower(),
        )
    }
    # Supabase (and other) poolers reject Django server-side cursors.
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join("/data", "db.sqlite3"),
            "OPTIONS": {"timeout": 20},
        }
    }
