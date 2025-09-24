from django.conf import settings
from django.db import models
from model_utils import Choices
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class Notification(SoftDeletableModel, UUIDModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    subject = models.CharField(max_length=255)
    message = models.TextField()
    STATUS = Choices(
        ("sent", "Sent"),
        ("enqueued", "Enqueued"),
    )
    TRANSPORT = Choices(
        ("mail", "Mail"),
        ("sms", "SMS"),
        ("other", "Other"),
    )
    status = models.CharField(max_length=10, choices=STATUS, default=STATUS.enqueued)
    transport = models.CharField(max_length=10, choices=TRANSPORT, default=TRANSPORT.mail)
