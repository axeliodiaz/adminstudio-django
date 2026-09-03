from django.conf import settings
from django.db import models
from django.db.models import Q
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel

from apps.members import constants
from apps.instructors.models import Instructor
from apps.schedules.models import Schedule
from apps.studios.models import Room


class Member(SoftDeletableModel, UUIDModel, TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member"
    )

    def __str__(self):
        return self.user.username


class FavoriteInstructor(UUIDModel, TimeStampedModel):
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="favorite_instructors"
    )
    instructor = models.ForeignKey(
        Instructor, on_delete=models.CASCADE, related_name="favorited_by_members"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["member", "instructor"], name="uniq_favorite_instructor_per_member"
            )
        ]


class FavoriteTimeSlot(UUIDModel, TimeStampedModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="favorite_time_slots")
    weekday = models.PositiveSmallIntegerField(help_text="Monday is 0 and Sunday is 6.")
    start_hour = models.PositiveSmallIntegerField()
    end_hour = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(weekday__gte=0, weekday__lte=6),
                name="favorite_time_slot_weekday_range",
            ),
            models.CheckConstraint(
                condition=Q(start_hour__gte=0, start_hour__lte=23),
                name="favorite_time_slot_start_hour_range",
            ),
            models.CheckConstraint(
                condition=Q(end_hour__gte=1, end_hour__lte=24),
                name="favorite_time_slot_end_hour_range",
            ),
            models.CheckConstraint(
                condition=Q(end_hour__gt=models.F("start_hour")),
                name="favorite_time_slot_positive_duration",
            ),
            models.UniqueConstraint(
                fields=["member", "weekday", "start_hour", "end_hour"],
                name="uniq_favorite_time_slot_per_member",
            ),
        ]


class FavoriteSpot(UUIDModel, TimeStampedModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="favorite_spots")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="favorite_spots")
    spot = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(spot__gt=0), name="favorite_spot_positive"),
            models.UniqueConstraint(
                fields=["member", "room", "spot"], name="uniq_favorite_spot_per_member"
            ),
        ]


class AlertPreference(UUIDModel, TimeStampedModel):
    """Email alert choices. Quiet hours use the Django default timezone."""

    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name="alert_preference")
    email_enabled = models.BooleanField(default=True)
    quiet_hours_start = models.PositiveSmallIntegerField(null=True, blank=True)
    quiet_hours_end = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quiet_hours_start__isnull=True)
                | Q(quiet_hours_start__gte=0, quiet_hours_start__lte=23),
                name="alert_preference_quiet_start_range",
            ),
            models.CheckConstraint(
                condition=Q(quiet_hours_end__isnull=True)
                | Q(quiet_hours_end__gte=0, quiet_hours_end__lte=23),
                name="alert_preference_quiet_end_range",
            ),
        ]


class AlertDelivery(UUIDModel, TimeStampedModel):
    """Persistent idempotency record for favorite-alert email attempts."""

    KIND_SCHEDULE = "SCHEDULE"
    KIND_SPOT = "SPOT"
    KIND_CHOICES = ((KIND_SCHEDULE, "Schedule"), (KIND_SPOT, "Spot"))

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="alert_deliveries")
    event_key = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["member", "event_key", "kind"], name="uniq_alert_delivery_event_member_kind"
            )
        ]


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
    credit_charged = models.BooleanField(
        default=False,
        help_text="True when a class credit was deducted from the wallet for this reservation.",
    )
    cancellation_source = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Who cancelled: member, studio (staff), or schedule (class cancelled).",
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
