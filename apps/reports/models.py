"""Precomputed report tables (CYC-440).

Owner rule: reports read precomputed data from their own tables, never live
aggregates. Rows stay fresh through event-driven updates
(``apps.reports.signals`` plus explicit refresh calls in the two bulk-update
paths of ``apps.members.services``), a full rebuild on every deploy
(``refresh_reports`` from render_start.sh) and a manual admin refresh
endpoint. There is no cron on the free tier by design.

Every table carries a nullable ``studio`` FK so per-studio scoping
(CYC-433) can be switched on without a data migration. Today only the
global (``studio=NULL``) scope is written; the unique constraints cover
both the global row and future per-studio rows.
"""

from django.db import models
from django.db.models import Q
from model_utils.models import TimeStampedModel, UUIDModel


class DailyMetrics(UUIDModel, TimeStampedModel):
    """One precomputed row per (date, studio scope).

    Bucketing rule: operational metrics (classes, reservations, waitlist,
    ratings) are bucketed by the local date of the class; commercial and
    communication metrics (purchases, gift cards, guest passes, referrals,
    notifications, clicks, new members) by the local date of the event.
    ``computed_at`` records the last refresh of the row.
    """

    studio = models.ForeignKey(
        "studios.Studio",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="daily_metrics",
        help_text="Studio scope. NULL is the global all-studios row (only scope written today).",
    )
    date = models.DateField(db_index=True)

    # Classes and attendance (class-date bucket).
    classes_total = models.PositiveIntegerField(default=0)
    classes_canceled = models.PositiveIntegerField(default=0)
    spots_capacity = models.PositiveIntegerField(default=0)
    reservations_booked = models.PositiveIntegerField(
        default=0, help_text="Occupied spots: reserved, attended or missed."
    )
    reservations_attended = models.PositiveIntegerField(default=0)
    reservations_missed = models.PositiveIntegerField(default=0)
    reservations_cancelled = models.PositiveIntegerField(default=0)
    occupancy_rate = models.FloatField(default=0.0, help_text="Booked / capacity, percent.")
    attendee_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Member ids who attended a class this day; powers retention reports.",
    )
    waitlist_entries = models.PositiveIntegerField(
        default=0, help_text="Waitlist entries created this day."
    )
    waitlist_converted = models.PositiveIntegerField(
        default=0, help_text="Conversions on classes held this day."
    )

    # Revenue and purchases (event-date bucket, CLP).
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    purchases_count = models.PositiveIntegerField(default=0)
    first_time_buyers = models.PositiveIntegerField(default=0)
    returning_buyers = models.PositiveIntegerField(default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    promo_uses = models.PositiveIntegerField(default=0)
    revenue_by_plan = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"<plan name>": {"revenue": <clp>, "count": <n>}} for the day.',
    )

    # Gifts, guest passes and referrals (event-date bucket).
    gift_cards_sold = models.PositiveIntegerField(default=0)
    gift_cards_redeemed = models.PositiveIntegerField(default=0)
    guest_passes_issued = models.PositiveIntegerField(default=0)
    guest_passes_claimed = models.PositiveIntegerField(default=0)
    guest_passes_attended = models.PositiveIntegerField(default=0)
    referrals_signed_up = models.PositiveIntegerField(default=0)
    referrals_converted = models.PositiveIntegerField(default=0)

    # Communications (event-date bucket).
    notifications_sent = models.PositiveIntegerField(default=0)
    link_clicks = models.PositiveIntegerField(default=0)

    # Ratings (class-date bucket).
    ratings_count = models.PositiveIntegerField(default=0)
    rating_avg = models.FloatField(null=True, blank=True)

    new_members = models.PositiveIntegerField(default=0)

    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["date"],
                condition=Q(studio__isnull=True),
                name="uniq_dailymetrics_global_date",
            ),
            models.UniqueConstraint(
                fields=["date", "studio"],
                condition=Q(studio__isnull=False),
                name="uniq_dailymetrics_studio_date",
            ),
        ]
        indexes = [models.Index(fields=["studio", "date"], name="dailymetrics_scope_date_idx")]

    def __str__(self):
        return f"DailyMetrics {self.date} ({self.studio_id or 'global'})"


class ClassMetrics(UUIDModel, TimeStampedModel):
    """One precomputed row per non-draft class (schedule)."""

    schedule = models.OneToOneField(
        "schedules.Schedule", on_delete=models.CASCADE, related_name="report_metrics"
    )
    studio = models.ForeignKey(
        "studios.Studio",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="class_metrics",
    )
    instructor = models.ForeignKey(
        "instructors.Instructor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="class_metrics",
    )
    date = models.DateField(db_index=True)
    title = models.CharField(max_length=255, blank=True)
    is_canceled = models.BooleanField(default=False)
    capacity = models.PositiveIntegerField(default=0)
    booked = models.PositiveIntegerField(default=0)
    attended = models.PositiveIntegerField(default=0)
    missed = models.PositiveIntegerField(default=0)
    cancelled = models.PositiveIntegerField(default=0)
    waitlist_count = models.PositiveIntegerField(default=0)
    waitlist_converted = models.PositiveIntegerField(default=0)
    occupancy_rate = models.FloatField(default=0.0)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    rating_count = models.PositiveIntegerField(default=0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["instructor", "date"], name="classmetrics_coach_date_idx"),
            models.Index(fields=["studio", "date"], name="classmetrics_scope_date_idx"),
        ]

    def __str__(self):
        return f"ClassMetrics {self.title or self.schedule_id} ({self.date})"
