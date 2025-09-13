# Unified settings entrypoint selecting between local/prod and avoiding
# ambiguity with the inner settings package.
import os
from importlib import import_module

_env = os.environ.get("DJANGO_ENV", "local").lower()
if _env not in {"local", "prod"}:
    _env = "local"
# Explicit absolute import to the package module, then copy UPPERCASE attrs
_module = import_module(f"adminstudio_django.settings.{_env}")
for _k, _v in _module.__dict__.items():
    if _k.isupper():
        globals()[_k] = _v
