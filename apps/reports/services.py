"""Recompute engine and read builders for the precomputed reports (CYC-440).

Freshness model (no cron on the free tier):

- ``post_save`` signals recompute the affected day/class on every write.
- The two queryset ``.update()`` paths in ``apps.members.services`` (which
  bypass signals) call :func:`refresh_schedules` explicitly.
- ``refresh_reports`` rebuilds everything on every deploy and
  ``POST /api/reports/refresh/`` does the same on demand.

Recompute halves: ``recompute_day_classes`` touches the class/attendance
side (ClassMetrics rows + the class-date fields of DailyMetrics) and
``recompute_day_commercial`` touches the event-date side. Signal handlers
pick the half their event belongs to; ``recompute_day`` does both.
"""

import logging
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Min, Sum
from django.utils import timezone

from apps.analytics.constants import OCCUPIED_RESERVATION_STATUSES
from apps.coach.models import ClassRating
from apps.communications.models import TrackedLinkClick
from apps.members import constants as member_constants
from apps.members.models import Member, Reservation, WaitlistEntry
from apps.notifications.models import Notification
from apps.referrals.models import Referral
from apps.reports.models import ClassMetrics, DailyMetrics
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule
from apps.wallets.models import GiftCard, GuestPassInvitation, PlanPurchase

logger = logging.getLogger(__name__)

# Reports never go further back than this, even with a wider range requested.
MAX_RANGE_DAYS = 400
DEFAULT_RANGE_DAYS = 30


def local_date(dt):
    """Local (studio) calendar date of an aware datetime."""
    return timezone.localtime(dt).date()


def _day_bounds(day):
    start = timezone.make_aware(datetime.combine(day, time.min))
    return start, start + timedelta(days=1)


def _on_day(qs, field, day):
    start, end = _day_bounds(day)
    return qs.filter(**{f"{field}__gte": start, f"{field}__lt": end})


# ---------------------------------------------------------------------------
# Recompute: class / attendance half (class-date bucket)
# ---------------------------------------------------------------------------


def recompute_class_metrics(schedule):
    """Upsert the ClassMetrics row for one class. Returns the row."""
    status_counts = (
        Reservation.objects.filter(schedule=schedule, is_removed=False)
        .values("status")
        .annotate(n=Count("id"))
    )
    by_status = {row["status"]: row["n"] for row in status_counts}
    booked = sum(by_status.get(status, 0) for status in OCCUPIED_RESERVATION_STATUSES)
    attended = by_status.get(member_constants.RESERVATION_STATUS_ATTENDED, 0)
    missed = by_status.get(member_constants.RESERVATION_STATUS_MISSED, 0)
    cancelled = by_status.get(member_constants.RESERVATION_STATUS_CANCELLED, 0)

    waitlist_counts = (
        WaitlistEntry.objects.filter(schedule=schedule, is_removed=False)
        .values("status")
        .annotate(n=Count("id"))
    )
    waitlist_by_status = {row["status"]: row["n"] for row in waitlist_counts}
    waitlist_count = sum(waitlist_by_status.values())
    waitlist_converted = waitlist_by_status.get(member_constants.WAITLIST_STATUS_CONVERTED, 0)

    capacity = schedule.room.capacity if schedule.room_id and schedule.room else 0
    is_canceled = schedule.status == schedule_constants.SCHEDULE_STATUS_CANCELED
    rating_obj = ClassRating.objects.filter(schedule=schedule, is_removed=False).first()

    row, _ = ClassMetrics.objects.update_or_create(
        schedule=schedule,
        defaults={
            "studio_id": schedule.room.studio_id if schedule.room_id and schedule.room else None,
            "instructor_id": schedule.instructor_id,
            "date": local_date(schedule.start_time),
            "title": schedule.title or "",
            "is_canceled": is_canceled,
            "capacity": capacity,
            "booked": booked,
            "attended": attended,
            "missed": missed,
            "cancelled": cancelled,
            "waitlist_count": waitlist_count,
            "waitlist_converted": waitlist_converted,
            "occupancy_rate": round(booked / capacity * 100, 1) if capacity else 0.0,
            "rating": rating_obj.rating if rating_obj else None,
            "rating_count": rating_obj.rating_count if rating_obj else 0,
        },
    )
    return row


def recompute_day_classes(day, studio=None):
    """Recompute every ClassMetrics row of the day and the class half of DailyMetrics."""
    start, end = _day_bounds(day)
    schedules = list(
        Schedule.objects.filter(is_removed=False, start_time__gte=start, start_time__lt=end)
        .exclude(status=schedule_constants.SCHEDULE_STATUS_DRAFT)
        .select_related("room")
    )
    for schedule in schedules:
        recompute_class_metrics(schedule)

    valid_ids = {schedule.id for schedule in schedules}
    ClassMetrics.objects.filter(date=day, studio=studio).exclude(schedule_id__in=valid_ids).delete()

    rows = list(ClassMetrics.objects.filter(date=day, studio=studio))
    active = [row for row in rows if not row.is_canceled]
    capacity = sum(row.capacity for row in active)
    booked = sum(row.booked for row in active)
    attended = sum(row.attended for row in active)
    missed = sum(row.missed for row in active)
    cancelled = sum(row.cancelled for row in active)

    attendee_ids = sorted(
        {
            str(member_id)
            for member_id in Reservation.objects.filter(
                schedule_id__in=valid_ids,
                is_removed=False,
                status=member_constants.RESERVATION_STATUS_ATTENDED,
            ).values_list("member_id", flat=True)
        }
    )

    rated = [row for row in active if row.rating is not None]
    ratings_count = sum(row.rating_count for row in rated)
    rating_avg = round(sum(float(row.rating) for row in rated) / len(rated), 2) if rated else None

    defaults = {
        "classes_total": len(rows),
        "classes_canceled": sum(1 for row in rows if row.is_canceled),
        "spots_capacity": capacity,
        "reservations_booked": booked,
        "reservations_attended": attended,
        "reservations_missed": missed,
        "reservations_cancelled": cancelled,
        "occupancy_rate": round(booked / capacity * 100, 1) if capacity else 0.0,
        "attendee_ids": attendee_ids,
        "waitlist_entries": _on_day(
            WaitlistEntry.objects.filter(is_removed=False), "created", day
        ).count(),
        "waitlist_converted": sum(row.waitlist_converted for row in rows),
        "ratings_count": ratings_count,
        "rating_avg": rating_avg,
    }
    row, _ = DailyMetrics.objects.update_or_create(date=day, studio=studio, defaults=defaults)
    return row


# ---------------------------------------------------------------------------
# Recompute: commercial / communications half (event-date bucket)
# ---------------------------------------------------------------------------


def recompute_day_commercial(day, studio=None):
    """Recompute the event-date fields of the DailyMetrics row."""
    purchases = PlanPurchase.objects.all()
    day_purchases = list(_on_day(purchases, "created", day).select_related("plan"))

    revenue = sum((purchase.price_paid for purchase in day_purchases), Decimal("0"))
    discount_total = sum((purchase.discount_amount for purchase in day_purchases), Decimal("0"))
    by_plan = defaultdict(lambda: {"revenue": 0.0, "count": 0})
    for purchase in day_purchases:
        plan_name = purchase.plan.name if purchase.plan_id and purchase.plan else "Sin plan"
        by_plan[plan_name]["revenue"] += float(purchase.price_paid)
        by_plan[plan_name]["count"] += 1

    start, _ = _day_bounds(day)
    first_time_buyers = 0
    returning_buyers = 0
    for user_id in {purchase.user_id for purchase in day_purchases}:
        if purchases.filter(user_id=user_id, created__lt=start).exists():
            returning_buyers += 1
        else:
            first_time_buyers += 1

    defaults = {
        "revenue": revenue,
        "purchases_count": len(day_purchases),
        "first_time_buyers": first_time_buyers,
        "returning_buyers": returning_buyers,
        "discount_total": discount_total,
        "promo_uses": sum(1 for purchase in day_purchases if purchase.promo_code_id),
        "revenue_by_plan": dict(by_plan),
        "gift_cards_sold": _on_day(GiftCard.objects.all(), "created", day).count(),
        "gift_cards_redeemed": _on_day(
            GiftCard.objects.exclude(redeemed_at__isnull=True), "redeemed_at", day
        ).count(),
        "guest_passes_issued": _on_day(GuestPassInvitation.objects.all(), "created", day).count(),
        "guest_passes_claimed": _on_day(
            GuestPassInvitation.objects.exclude(claimed_at__isnull=True), "claimed_at", day
        ).count(),
        "guest_passes_attended": _on_day(
            GuestPassInvitation.objects.exclude(reservation__attended_at__isnull=True),
            "reservation__attended_at",
            day,
        ).count(),
        "referrals_signed_up": _on_day(Referral.objects.all(), "signed_up_at", day).count(),
        "referrals_converted": _on_day(
            Referral.objects.exclude(converted_at__isnull=True), "converted_at", day
        ).count(),
        "notifications_sent": _on_day(
            Notification.objects.filter(is_removed=False, status=Notification.STATUS.sent),
            "created",
            day,
        ).count(),
        "link_clicks": _on_day(TrackedLinkClick.objects.all(), "created", day).count(),
        "new_members": _on_day(Member.objects.filter(is_removed=False), "created", day).count(),
    }
    row, _ = DailyMetrics.objects.update_or_create(date=day, studio=studio, defaults=defaults)
    return row


def recompute_day(day, studio=None):
    """Recompute both halves of a day. Returns the DailyMetrics row."""
    recompute_day_classes(day, studio=studio)
    return recompute_day_commercial(day, studio=studio)


def refresh_schedules(schedule_ids):
    """Refresh the ClassMetrics rows and days for a set of schedules.

    Called explicitly from bulk-update paths in ``apps.members.services``
    (queryset ``.update()`` bypasses the ``post_save`` signals).
    """
    days = set()
    for schedule in Schedule.objects.filter(id__in=set(schedule_ids)).select_related("room"):
        recompute_class_metrics(schedule)
        days.add(local_date(schedule.start_time))
    for day in days:
        recompute_day_classes(day)
    return len(days)


def _first_event_date():
    """Earliest date with reportable activity across every source table."""
    sources = [
        (Schedule.objects.filter(is_removed=False), "start_time"),
        (PlanPurchase.objects.all(), "created"),
        (GiftCard.objects.all(), "created"),
        (GuestPassInvitation.objects.all(), "created"),
        (Referral.objects.all(), "signed_up_at"),
        (WaitlistEntry.objects.filter(is_removed=False), "created"),
        (Member.objects.filter(is_removed=False), "created"),
        (Notification.objects.filter(is_removed=False), "created"),
        (TrackedLinkClick.objects.all(), "created"),
    ]
    dates = []
    for queryset, field in sources:
        earliest = queryset.aggregate(first=Min(field))["first"]
        if earliest:
            dates.append(local_date(earliest))
    return min(dates) if dates else None


def refresh_all():
    """Full rebuild of every precomputed row. Returns a summary dict."""
    today = timezone.localdate()
    first_day = _first_event_date() or today
    days = (today - first_day).days + 1
    for offset in range(days):
        recompute_day(first_day + timedelta(days=offset))
    # Drop ClassMetrics rows whose schedule became a draft or was removed.
    valid_schedule_ids = (
        Schedule.objects.filter(is_removed=False)
        .exclude(status=schedule_constants.SCHEDULE_STATUS_DRAFT)
        .values("id")
    )
    ClassMetrics.objects.exclude(schedule_id__in=valid_schedule_ids).delete()
    return {
        "first_day": first_day.isoformat(),
        "last_day": today.isoformat(),
        "days_recomputed": days,
        "classes_recomputed": ClassMetrics.objects.count(),
    }
