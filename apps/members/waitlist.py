from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.members import constants
from apps.members.exceptions import WaitlistException
from apps.members.models import Member, Reservation, WaitlistEntry
from apps.schedules.schedules import get_schedule_by_id


def reserved_count_for_schedule(schedule_id: str | UUID) -> int:
    return Reservation.objects.filter(
        schedule_id=schedule_id,
        status=constants.RESERVATION_STATUS_RESERVED,
        is_removed=False,
    ).count()


def is_schedule_full(schedule) -> bool:
    capacity = schedule.room.capacity if schedule.room else 0
    return reserved_count_for_schedule(schedule.id) >= capacity


def active_waitlist_queryset(schedule_id: str | UUID | None = None) -> QuerySet[WaitlistEntry]:
    qs = WaitlistEntry.objects.filter(
        is_removed=False,
        status__in=constants.WAITLIST_ACTIVE_STATUSES,
    )
    if schedule_id is not None:
        qs = qs.filter(schedule_id=schedule_id)
    return qs.order_by("created")


def waitlist_position(entry: WaitlistEntry) -> int:
    earlier = active_waitlist_queryset(entry.schedule_id).filter(created__lt=entry.created).count()
    return earlier + 1


def expire_stale_offers(
    schedule_id: str | UUID | None = None, *, promote: bool = True
) -> list[WaitlistEntry]:
    """Mark expired OFFERED entries and optionally offer the spot to the next member."""
    now = timezone.now()
    qs = WaitlistEntry.objects.filter(
        is_removed=False,
        status=constants.WAITLIST_STATUS_OFFERED,
        offer_expires_at__isnull=False,
        offer_expires_at__lte=now,
    )
    if schedule_id is not None:
        qs = qs.filter(schedule_id=schedule_id)

    expired = list(qs)
    for entry in expired:
        entry.status = constants.WAITLIST_STATUS_EXPIRED
        entry.save(update_fields=["status", "modified"])

    if promote:
        for entry in expired:
            if entry.offered_spot:
                promote_waitlist_for_schedule(entry.schedule_id, entry.offered_spot)
    return expired


def expire_waitlist_for_cancelled_schedule(schedule_id: str | UUID) -> int:
    """Expire all active waitlist entries when a class is cancelled by the studio."""
    entries = list(active_waitlist_queryset(schedule_id))
    for entry in entries:
        entry.status = constants.WAITLIST_STATUS_EXPIRED
        entry.save(update_fields=["status", "modified"])
    return len(entries)


def join_waitlist(*, user_id: str | UUID, schedule_id: str | UUID) -> WaitlistEntry:
    member = Member.objects.get(user_id=user_id)
    schedule = get_schedule_by_id(schedule_id)

    existing_reservation = Reservation.objects.filter(
        member=member,
        schedule=schedule,
        status=constants.RESERVATION_STATUS_RESERVED,
        is_removed=False,
    ).first()
    if existing_reservation:
        raise WaitlistException("Ya tienes una reserva para esta clase.")

    expire_stale_offers(schedule.id)

    existing = active_waitlist_queryset(schedule.id).filter(member=member).first()
    if existing:
        return existing

    if not is_schedule_full(schedule):
        raise WaitlistException("La clase aún tiene cupos. Reserva un spot.")

    return WaitlistEntry.objects.create(
        member=member,
        schedule=schedule,
        status=constants.WAITLIST_STATUS_WAITING,
    )


def leave_waitlist(*, user_id: str | UUID, waitlist_id: str | UUID) -> WaitlistEntry:
    member = Member.objects.get(user_id=user_id)
    entry = WaitlistEntry.objects.get(id=waitlist_id, member=member, is_removed=False)
    if entry.status not in constants.WAITLIST_ACTIVE_STATUSES:
        raise WaitlistException("Esta entrada de lista de espera ya no está activa.")

    schedule_id = entry.schedule_id
    offered_spot = entry.offered_spot if entry.status == constants.WAITLIST_STATUS_OFFERED else None
    entry.status = constants.WAITLIST_STATUS_LEFT
    entry.save(update_fields=["status", "modified"])

    if offered_spot:
        promote_waitlist_for_schedule(schedule_id, offered_spot)
    return entry


def list_waitlist_for_user(*, user_id: str | UUID, schedule_id: str | UUID | None = None):
    member = Member.objects.get(user_id=user_id)
    expire_stale_offers()
    qs = (
        active_waitlist_queryset()
        .filter(member=member)
        .select_related("schedule__room__studio", "schedule__instructor__user")
    )
    if schedule_id:
        qs = qs.filter(schedule_id=schedule_id)
    return list(qs)


def confirm_waitlist_offer(*, user_id: str | UUID, waitlist_id: str | UUID) -> WaitlistEntry:
    from apps.members.members import create_reservation

    member = Member.objects.get(user_id=user_id)
    with transaction.atomic():
        expire_stale_offers()
        entry = WaitlistEntry.objects.select_for_update().get(
            id=waitlist_id, member=member, is_removed=False
        )
        if entry.status != constants.WAITLIST_STATUS_OFFERED:
            raise WaitlistException("No hay un cupo ofrecido para confirmar.")
        if entry.offer_expires_at and entry.offer_expires_at <= timezone.now():
            entry.status = constants.WAITLIST_STATUS_EXPIRED
            entry.save(update_fields=["status", "modified"])
            if entry.offered_spot:
                promote_waitlist_for_schedule(entry.schedule_id, entry.offered_spot)
            raise WaitlistException("El tiempo para confirmar el spot ya expiró.")

        reservation = create_reservation(
            {
                "user_id": user_id,
                "schedule_id": entry.schedule_id,
                "spot": entry.offered_spot,
                "notes": "Waitlist confirmation",
            }
        )
        entry.status = constants.WAITLIST_STATUS_CONVERTED
        entry.converted_reservation = reservation
        entry.save(update_fields=["status", "converted_reservation", "modified"])
        return entry


def _notify_waitlist_offer(entry: WaitlistEntry, auto_confirmed: bool) -> None:
    from django.conf import settings

    from apps.notifications.email_templates import render_waitlist_offer
    from apps.notifications.services import create_notification

    user = entry.member.user
    schedule = entry.schedule
    title = schedule.title or "clase"
    start = timezone.localtime(schedule.start_time).strftime("%d/%m/%Y %H:%M")
    frontend_url = (getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173").rstrip("/")
    minutes = constants.WAITLIST_OFFER_MINUTES
    spot = entry.offered_spot
    if auto_confirmed:
        subject = f"Spot confirmado en {title}"
        message = (
            f"Se liberó un cupo en {title} ({start}). "
            f"Como tienes auto-confirmación activa, reservamos el spot {spot} por ti."
        )
        action_url = f"{frontend_url}/#my-reservations"
    else:
        subject = f"Se liberó un spot en {title}"
        message = (
            f"Se liberó un cupo en {title} ({start}). "
            f"Tienes {minutes} minutos para confirmar tu spot {spot} "
            "desde Lista de espera en PulseFit."
        )
        action_url = f"{frontend_url}/#waitlist"
    create_notification(
        subject,
        message,
        [user],
        html_content=render_waitlist_offer(
            class_title=title,
            when_label=start,
            spot=spot,
            action_url=action_url,
            frontend_url=frontend_url,
            auto_confirmed=auto_confirmed,
            offer_minutes=minutes,
        ),
    )


def _convert_waitlist_entry(entry: WaitlistEntry, spot: int) -> WaitlistEntry:
    from apps.members.members import create_reservation

    reservation = create_reservation(
        {
            "user_id": entry.member.user_id,
            "schedule_id": entry.schedule_id,
            "spot": spot,
            "notes": "Waitlist auto-confirm",
        }
    )
    entry.status = constants.WAITLIST_STATUS_CONVERTED
    entry.offered_spot = spot
    entry.converted_reservation = reservation
    entry.save(update_fields=["status", "offered_spot", "converted_reservation", "modified"])
    _notify_waitlist_offer(entry, auto_confirmed=True)
    return entry


def promote_waitlist_for_schedule(
    schedule_id: str | UUID, freed_spot: int | None
) -> WaitlistEntry | None:
    """Offer (or auto-confirm) the next waiting member after a cancellation."""
    expire_stale_offers(schedule_id, promote=False)
    if not freed_spot:
        schedule = get_schedule_by_id(schedule_id)
        taken = set(
            Reservation.objects.filter(
                schedule_id=schedule_id,
                status=constants.RESERVATION_STATUS_RESERVED,
                is_removed=False,
                spot__isnull=False,
            ).values_list("spot", flat=True)
        )
        capacity = schedule.room.capacity if schedule.room else 0
        freed_spot = next((n for n in range(1, capacity + 1) if n not in taken), None)
        if not freed_spot:
            return None

    next_entry = (
        WaitlistEntry.objects.filter(
            schedule_id=schedule_id,
            is_removed=False,
            status=constants.WAITLIST_STATUS_WAITING,
        )
        .select_related("member__user", "schedule")
        .order_by("created")
        .first()
    )
    if not next_entry:
        return None

    user = next_entry.member.user
    if getattr(user, "waitlist_auto_confirm", False):
        return _convert_waitlist_entry(next_entry, freed_spot)

    now = timezone.now()
    next_entry.status = constants.WAITLIST_STATUS_OFFERED
    next_entry.offered_spot = freed_spot
    next_entry.offered_at = now
    next_entry.offer_expires_at = now + timedelta(minutes=constants.WAITLIST_OFFER_MINUTES)
    next_entry.save(
        update_fields=["status", "offered_spot", "offered_at", "offer_expires_at", "modified"]
    )
    _notify_waitlist_offer(next_entry, auto_confirmed=False)
    return next_entry
