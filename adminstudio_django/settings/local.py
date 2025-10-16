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
if DEBUG:
    INSTALLED_APPS += [
        "drf_yasg",
    ]
