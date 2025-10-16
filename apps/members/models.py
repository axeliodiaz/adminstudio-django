from django.conf import settings
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel

from apps.members import constants
from apps.schedules.models import Schedule


class Member(SoftDeletableModel, UUIDModel, TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member"
    )


class Reservation(SoftDeletableModel, UUIDModel, TimeStampedModel):
    STATUS_CHOICES = (
        (constants.RESERVATION_STATUS_RESERVED, "Reserved"),
        (constants.RESERVATION_STATUS_CANCELLED, "Cancelled"),
        (constants.RESERVATION_STATUS_ATTENDED, "Attended"),
        (constants.RESERVATION_STATUS_MISSED, "Missed"),  # no-show
    )

    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=constants.RESERVATION_STATUS_RESERVED,
    )
    notes = models.TextField(
        blank=True,
        help_text=(
            "Optional notes or remarks related to this reservation (e.g. late arrival, injury, manual adjustment)."
        ),
    )

    def __str__(self):
        return f"{self.member} → {self.schedule} ({self.status})"
