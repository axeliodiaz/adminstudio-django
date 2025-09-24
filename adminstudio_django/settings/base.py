import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-o!)ui_&!)=$2@f&_vlusf8!=5373r+sfamtim^6u0(x+elq06+",
)

# Default: production-safe unless overridden in local.py
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in {"1", "true", "yes", "on"}

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
CORE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
]
OWN_APPS = [
    "apps.healthcheck",
    "apps.users",
    "apps.riders",
    "apps.verifications",
    "apps.notifications",
    "apps.instructors",
]
INSTALLED_APPS = CORE_APPS + THIRD_PARTY_APPS + OWN_APPS

# Use custom user model
AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "adminstudio_django.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "adminstudio_django.wsgi.application"

# Database - keep sqlite by default
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"

# DRF defaults – JSON only by default; local.py will extend to add browsable renderer
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ]
}

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DEFAULT_PASSWORD_LENGTH = 13

EMAIL_HOST = os.getenv("EMAIL_HOST", "sandbox.smtp.mailtrap.io")
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "apikey")  # 'apikey' for Sendgrid
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = os.getenv("EMAIL_PORT", 2525)
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "noreply<no_reply@domain.com>"

VERIFICATION_CODE_EXPIRATION_MINUTES = 5

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Logging configuration
# Shows INFO and above in local by default, WARNING in production unless overridden.
DJANGO_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO" if DEBUG else "WARNING")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(name)s: %(message)s",
        },
        "verbose": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "verbose",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": DJANGO_LOG_LEVEL,
    },
    "loggers": {
        # Make Django's internal logs visible at INFO in development
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_DJANGO_LOG_LEVEL", "INFO" if DEBUG else "WARNING"),
            "propagate": False,
        },
        # Project apps (e.g., apps.notifications.mailing will match and propagate to root)
        "apps": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_APPS_LOG_LEVEL", "DEBUG" if DEBUG else "INFO"),
            "propagate": True,
        },
        # Celery logger (worker output)
        "celery": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_CELERY_LOG_LEVEL", "INFO"),
            "propagate": True,
        },
    },
}

CELERY_BROKER_URL = "amqp://guest:guest@rabbitmq:5672//"
CELERY_RESULT_BACKEND = "rpc://"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
