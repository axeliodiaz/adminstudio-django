from django.apps import AppConfig


class HealthcheckConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.healthcheck"

    def ready(self) -> None:
        # Register public API cache invalidation handlers (import side effects).
        from apps.common import public_cache_signals  # noqa: F401
