from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel


class Rider(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rider"
    )
