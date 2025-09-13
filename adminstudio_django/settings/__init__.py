# Settings package initializer: expose either .local or .prod
# so that DJANGO_SETTINGS_MODULE=adminstudio_django.settings works.
import os
from importlib import import_module

_env = os.environ.get("DJANGO_ENV", "local").lower()
if _env not in {"local", "prod"}:
    _env = "local"
_module = import_module(f"{__name__}.{_env}")
for _k, _v in _module.__dict__.items():
    if _k.isupper():
        globals()[_k] = _v
