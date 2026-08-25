"""Outbound member/reservation notifications."""

from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.notifications.email_templates import (
    render_booking_confirmed,
    render_class_cancelled,
)
from apps.notifications.services import create_notification
from apps.studios.models import StudioSettings

logger = logging.getLogger(__name__)

_LOCAL_TZ = ZoneInfo("America/Santiago")
_WEEKDAYS_ES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)
_MONTHS_SHORT_ES = (
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)


def _frontend_url() -> str:
    return (getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173").rstrip("/")


def _person_name(user) -> str:
    if not user:
        return ""
    full = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
    return full or (user.username or user.email or "")


def _format_when(start_time) -> str:
    local = (
        start_time.astimezone(_LOCAL_TZ)
        if start_time.tzinfo
        else start_time.replace(tzinfo=_LOCAL_TZ)
    )
    weekday = _WEEKDAYS_ES[local.weekday()].capitalize()
    month = _MONTHS_SHORT_ES[local.month - 1]
    return f"{weekday} {local.day} {month} · {local.strftime('%H:%M')}"


def _format_when_sentence(start_time) -> str:
    """Sketch copy: 'martes 26 ago a las 06:30'."""
    local = (
        start_time.astimezone(_LOCAL_TZ)
        if start_time.tzinfo
        else start_time.replace(tzinfo=_LOCAL_TZ)
    )
    weekday = _WEEKDAYS_ES[local.weekday()]
    month = _MONTHS_SHORT_ES[local.month - 1]
    return f"{weekday} {local.day} {month} a las {local.strftime('%H:%M')}"


def _subject_when(start_time) -> str:
    local = (
        start_time.astimezone(_LOCAL_TZ)
        if start_time.tzinfo
        else start_time.replace(tzinfo=_LOCAL_TZ)
    )
    return local.strftime("%H:%M")


def _load_reservation(reservation):
    return (
        type(reservation)
        .objects.select_related(
            "member__user",
            "schedule__instructor__user",
            "schedule__room__studio",
        )
        .get(pk=reservation.pk)
    )


def send_reservation_confirmed_email(reservation) -> None:
    """Send the booking-confirmed HTML email. Failures are logged, never raised."""
    try:
        reservation = _load_reservation(reservation)
        user = reservation.member.user
        schedule = reservation.schedule
        room = schedule.room
        studio = room.studio if room else None
        instructor_user = schedule.instructor.user if schedule.instructor_id else None

        first_name = (user.first_name or "").strip()
        class_title = (schedule.title or "Clase").strip() or "Clase"
        coach_name = _person_name(instructor_user) or "Coach"
        studio_name = (studio.name if studio else "PulseFit Studio").strip() or "PulseFit Studio"
        room_name = (room.name if room else "Sala").strip() or "Sala"
        when_label = _format_when(schedule.start_time)
        free_hours = StudioSettings.load().free_cancellation_hours

        frontend_url = _frontend_url()
        reservation_url = f"{frontend_url}/#my-reservations"
        subject = f"Reserva confirmada · {class_title} · {_subject_when(schedule.start_time)}"
        message = (
            f"Confirmamos tu reserva: {class_title} · {when_label} · "
            f"{room_name} · Spot {reservation.spot}. "
            f"Cancelación gratuita hasta {free_hours} horas antes. "
            f"Ver reserva: {reservation_url}"
        )

        create_notification(
            subject=subject,
            message=message,
            recipient_list=[user],
            html_content=render_booking_confirmed(
                first_name=first_name,
                class_title=class_title,
                coach_name=coach_name,
                when_label=when_label,
                duration_minutes=schedule.duration_minutes,
                studio_name=studio_name,
                room_name=room_name,
                spot=reservation.spot,
                reservation_url=reservation_url,
                frontend_url=frontend_url,
                free_cancellation_hours=free_hours,
            ),
        )
    except Exception:
        logger.exception(
            "Failed to send reservation confirmed email",
            extra={"reservation_id": str(getattr(reservation, "pk", ""))},
        )


def send_class_cancelled_email(
    reservation, *, reason: str = "", credit_refunded: bool | None = None
) -> None:
    """Send the class-cancelled HTML email. Failures are logged, never raised."""
    try:
        reservation = _load_reservation(reservation)
        user = reservation.member.user
        schedule = reservation.schedule
        instructor_user = schedule.instructor.user if schedule.instructor_id else None

        class_title = (schedule.title or "Clase").strip() or "Clase"
        coach_name = _person_name(instructor_user) or "Coach"
        when_sentence = _format_when_sentence(schedule.start_time)

        if credit_refunded is None:
            wallet = getattr(user, "wallet", None)
            credit_refunded = not bool(
                wallet and getattr(wallet, "is_unlimited_membership_active", False)
            )

        frontend_url = _frontend_url()
        classes_url = f"{frontend_url}/#classes"
        subject = f"Clase cancelada · {class_title} {_subject_when(schedule.start_time)}"
        reason_text = (reason or "").strip() or "Cancelación del estudio"
        credit_msg = "Devolvimos el crédito a tu billetera. " if credit_refunded else ""
        message = (
            f"Cancelamos {class_title} ({when_sentence}). "
            f"Motivo: {reason_text}. "
            f"{credit_msg}"
            f"Ver otras clases: {classes_url}"
        )

        create_notification(
            subject=subject,
            message=message,
            recipient_list=[user],
            html_content=render_class_cancelled(
                class_title=class_title,
                coach_name=coach_name,
                when_label=when_sentence,
                reason=reason_text,
                classes_url=classes_url,
                frontend_url=frontend_url,
                credit_refunded=credit_refunded,
            ),
        )
    except Exception:
        logger.exception(
            "Failed to send class cancelled email",
            extra={"reservation_id": str(getattr(reservation, "pk", ""))},
        )
