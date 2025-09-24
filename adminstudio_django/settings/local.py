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
]

# Mailtrap sandbox SMTP for local/dev
EMAIL_HOST = "sandbox.smtp.mailtrap.io"
EMAIL_HOST_USER = "be291a2b93d0d6"
EMAIL_HOST_PASSWORD = "7ea7e9f51cc69f"
EMAIL_PORT = 2525
# For local Mailtrap, avoid TLS to bypass certificate verification entirely (dev only)
EMAIL_USE_TLS = False

# Note: EMAIL_TLS_VERIFY is only used by the previously custom backend and is not needed now.

"""
EMAIL_HOST_PASSWORD = "4c001817abf9cd731b90cd7f90892efc"
EMAIL_HOST = "sandbox.smtp.mailtrap.io"
EMAIL_PORT = "2525"
EMAIL_HOST_USER = "be291a2b93d0d6"
EMAIL_USE_TLS = True
# EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = "no-reply@adminstudio.local"
"""
