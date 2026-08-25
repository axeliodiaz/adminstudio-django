from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel

from apps.instructors.models import Instructor
from apps.schedules import constants
from apps.studios.models import Room


class Schedule(UUIDModel, SoftDeletableModel, TimeStampedModel):
    STATUS = [
        (constants.SCHEDULE_STATUS_DRAFT, "Draft"),
        (constants.SCHEDULE_STATUS_SCHEDULED, "Scheduled"),
        (constants.SCHEDULE_STATUS_COMPLETED, "Completed"),
        (constants.SCHEDULE_STATUS_CANCELED, "Canceled"),
    ]
    title = models.CharField(max_length=255, default="")
    description = models.TextField(blank=True, null=True)
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=45)
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default=constants.SCHEDULE_STATUS_DRAFT,
    )
    cancellation_reason = models.TextField(
        blank=True,
        default="",
        help_text="Optional reason shown to members when the class is cancelled.",
    )

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.title} - {self.start_time})"
