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
