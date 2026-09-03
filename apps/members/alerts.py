"""Event-driven favorite-alert delivery. There is deliberately no scheduler or retry job."""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.members import constants
from apps.members.models import (
    AlertDelivery,
    AlertPreference,
    FavoriteInstructor,
    FavoriteSpot,
    FavoriteTimeSlot,
    Member,
    Reservation,
    WaitlistEntry,
)
from apps.schedules.constants import SCHEDULE_STATUS_SCHEDULED

logger = logging.getLogger(__name__)
DAILY_ALERT_LIMIT = 5


def _preference_allows(member) -> bool:
    preference, _ = AlertPreference.objects.get_or_create(member=member)
    if not preference.email_enabled or not member.user.email:
        return False
    if preference.quiet_hours_start is None or preference.quiet_hours_end is None:
        return True
    # Equal values mean quiet hours are disabled, avoiding an ambiguous all-day mute.
    if preference.quiet_hours_start == preference.quiet_hours_end:
        return True
    hour = timezone.localtime().hour
    start, end = preference.quiet_hours_start, preference.quiet_hours_end
    return not (start <= hour < end if start < end else hour >= start or hour < end)


def _has_priority_or_member_interest(member, schedule) -> bool:
    return (
        Reservation.objects.filter(
            member=member,
            schedule=schedule,
            is_removed=False,
            status=constants.RESERVATION_STATUS_RESERVED,
        ).exists()
        or WaitlistEntry.objects.filter(
            member=member,
            schedule=schedule,
            is_removed=False,
            status__in=constants.WAITLIST_ACTIVE_STATUSES,
        ).exists()
    )


def _record_and_send(*, member, event_key: str, kind: str, subject: str, message: str) -> None:
    """Serialize per-member writes in Postgres, then keep delivery failure non-fatal."""
    if not _preference_allows(member):
        return
    try:
        with transaction.atomic():
            # Locks make the daily count + idempotency insert safe across concurrent event requests.
            member = Member.objects.select_for_update().get(pk=member.pk)
            today = timezone.localdate()
            if (
                AlertDelivery.objects.filter(member=member, created__date=today).count()
                >= DAILY_ALERT_LIMIT
            ):
                return
            AlertDelivery.objects.create(member=member, event_key=event_key, kind=kind)
    except IntegrityError:
        return

    try:
        from apps.notifications.services import create_notification

        create_notification(subject, message, [member.user])
    except Exception:
        # The business event has already committed. A failed email must never undo it.
        logger.exception(
            "Favorite alert email failed",
            extra={"member_id": str(member.id), "event_key": event_key, "kind": kind},
        )


def notify_schedule_available(schedule) -> None:
    """Email members whose instructor or local weekday/hour favorite matches a scheduled class."""
    if schedule.status != SCHEDULE_STATUS_SCHEDULED:
        return
    local_start = timezone.localtime(schedule.start_time)
    members = set(
        FavoriteInstructor.objects.filter(instructor_id=schedule.instructor_id).values_list(
            "member_id", flat=True
        )
    )
    members.update(
        FavoriteTimeSlot.objects.filter(
            weekday=local_start.weekday(),
            start_hour__lte=local_start.hour,
            end_hour__gt=local_start.hour,
        ).values_list("member_id", flat=True)
    )
    for member_id in members:
        member = Member.objects.select_related("user").get(pk=member_id)
        if not _has_priority_or_member_interest(member, schedule):
            _record_and_send(
                member=member,
                event_key=f"schedule:{schedule.id}",
                kind=AlertDelivery.KIND_SCHEDULE,
                subject=f"Nueva clase disponible: {schedule.title or 'clase'}",
                message=f"Hay una nueva clase el {local_start.strftime('%d/%m a las %H:%M')}.",
            )


def notify_favorite_spot_available(schedule, spot: int | None) -> None:
    """Email only after waitlist promotion has found no claimant for a freed spot."""
    if (
        not spot
        or WaitlistEntry.objects.filter(
            schedule=schedule, is_removed=False, status__in=constants.WAITLIST_ACTIVE_STATUSES
        ).exists()
    ):
        return
    members = FavoriteSpot.objects.filter(room_id=schedule.room_id, spot=spot).select_related(
        "member__user"
    )
    for favorite in members:
        if not _has_priority_or_member_interest(favorite.member, schedule):
            _record_and_send(
                member=favorite.member,
                event_key=f"spot:{schedule.id}:{spot}",
                kind=AlertDelivery.KIND_SPOT,
                subject=f"Spot {spot} disponible",
                message=f"Se liberó tu spot favorito {spot} en {schedule.title or 'una clase'}.",
            )
