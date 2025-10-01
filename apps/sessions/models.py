from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel

from apps.instructors.models import Instructor
from apps.sessions import constants
from apps.studios.models import StudioRoom


class Session(UUIDModel, SoftDeletableModel, TimeStampedModel):
    STATUS = [
        (constants.SESSION_STATUS_DRAFT, "Draft"),
        (constants.SESSION_STATUS_SCHEDULED, "Scheduled"),
        (constants.SESSION_STATUS_COMPLETED, "Completed"),
        (constants.SESSION_STATUS_CANCELED, "Canceled"),
    ]
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=45)
    room = models.ForeignKey(
        StudioRoom,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default=constants.SESSION_STATUS_DRAFT,
    )

    class Meta:
        ordering = ["start_time"]
