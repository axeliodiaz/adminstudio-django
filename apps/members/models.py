from django.conf import settings
from django.db import models
from django.db.models import Q
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel

from apps.members import constants
from apps.schedules.models import Schedule


class Member(SoftDeletableModel, UUIDModel, TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member"
    )

    def __str__(self):
        return self.user.username


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
    spot = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="The bike spot/puesto number chosen for this reservation.",
    )

    def __str__(self):
        return f"{self.member} → {self.schedule} ({self.status})"


class WaitlistEntry(SoftDeletableModel, UUIDModel, TimeStampedModel):
    STATUS_CHOICES = (
        (constants.WAITLIST_STATUS_WAITING, "Waiting"),
        (constants.WAITLIST_STATUS_OFFERED, "Offered"),
        (constants.WAITLIST_STATUS_CONVERTED, "Converted"),
        (constants.WAITLIST_STATUS_LEFT, "Left"),
        (constants.WAITLIST_STATUS_EXPIRED, "Expired"),
    )

    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=constants.WAITLIST_STATUS_WAITING,
    )
    offered_spot = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Spot offered to this member when a reservation is cancelled.",
    )
    offered_at = models.DateTimeField(null=True, blank=True)
    offer_expires_at = models.DateTimeField(null=True, blank=True)
    converted_reservation = models.ForeignKey(
        Reservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waitlist_conversions",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["member", "schedule"],
                condition=Q(
                    is_removed=False,
                    status__in=constants.WAITLIST_ACTIVE_STATUSES,
                ),
                name="uniq_active_waitlist_member_schedule",
            )
        ]

    def __str__(self):
        return f"{self.member} waitlist {self.schedule} ({self.status})"
