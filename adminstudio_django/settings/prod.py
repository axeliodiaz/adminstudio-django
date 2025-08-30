from .base import *  # noqa

# Production overrides
DEBUG = False

# Ensure Browsable API is disabled (JSON only from base)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
]

# Hosts can be provided via env; keep the one already used plus sane defaults
ALLOWED_HOSTS = ALLOWED_HOSTS  # from base; override via DJANGO_ALLOWED_HOSTS
