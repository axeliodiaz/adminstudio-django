import os

# Ensure Django settings are configured for pytest even if pytest-django plugin isn't active
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "adminstudio_django.settings.local")

try:
    import django  # noqa: F401
except Exception:  # pragma: no cover
    django = None

if django and not os.environ.get("_DJANGO_SETUP_DONE"):
    # Avoid repeated setup in sub-processes
    os.environ["_DJANGO_SETUP_DONE"] = "1"
    django.setup()
