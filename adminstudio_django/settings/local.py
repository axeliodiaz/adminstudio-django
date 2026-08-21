from .base import *  # noqa

# Local/development overrides
DEBUG = True

# Allow browsable API locally and admin static
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "rest_framework.schemas.coreapi.AutoSchema"


ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]
INSTALLED_APPS += [
    "drf_yasg",
    "corsheaders",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    *MIDDLEWARE,
]

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5174",
    "http://localhost:5173",  # frontend (Vite)
    "http://localhost:3000",  # opcional, por si se usa create-react-app
]
CORS_ALLOW_ALL_ORIGINS = True
"""
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
]
"""

CORS_ALLOW_CREDENTIALS = True
# Mailtrap API Key - Get it from https://mailtrap.io/ -> Settings -> API Tokens
# Set it as environment variable: export MAILTRAP_API_KEY="your_token_here"
MAILTRAP_API_KEY = os.getenv("MAILTRAP_API_KEY")
if not MAILTRAP_API_KEY:
    import warnings

    warnings.warn(
        "MAILTRAP_API_KEY is not set. Email sending via Mailtrap will fail. "
        "Get your API token from https://mailtrap.io/ -> Settings -> API Tokens",
        UserWarning,
    )
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")

# Celery: Run tasks synchronously in local development (no RabbitMQ needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
