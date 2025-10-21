from django.apps import AppConfig
from django.conf import settings
from mongoengine import connect
import os


class PlansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.plans"

    def ready(self):
        connect(
            db=settings.MONGO_CONFIG["db"],
            host=f"mongodb://{settings.MONGO_HOST}:{settings.MONGO_PORT}/{settings.MONGO_DB_NAME}",
            alias="default",
        )
