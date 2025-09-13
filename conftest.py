import os

# Ensure Django settings are configured for pytest even if pytest-django plugin isn't active
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "adminstudio_django.settings")

try:
    import django  # noqa: F401
except Exception:  # pragma: no cover
    django = None

if django and not os.environ.get("_DJANGO_SETUP_DONE"):
    # Avoid repeated setup in sub-processes
    os.environ["_DJANGO_SETUP_DONE"] = "1"
    django.setup()
    try:
        from django.core.management import call_command

        # Run migrations to ensure test DB has required tables
        call_command("migrate", verbosity=0, interactive=False)
    except Exception:
        # In case migrate isn't available for some reason in CI, ignore to not break import
        pass
