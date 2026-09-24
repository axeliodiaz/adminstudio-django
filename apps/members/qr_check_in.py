from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.members import constants
from apps.members.exceptions import ReservationInvalidStateException
from apps.members.members import MEMBER_CHECK_IN_WINDOW_MESSAGE, set_reservation_attendance
from apps.members.models import Reservation
from apps.members.schemas import ReservationSchema
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule

QR_TOKEN_SALT = "members.schedule-qr-check-in"
QR_INVALID_MESSAGE = "El QR no es válido o fue regenerado."
QR_NO_RESERVATION_MESSAGE = "No tienes una reserva activa para esta clase."
QR_CANCELLED_CLASS_MESSAGE = "No se puede confirmar asistencia a una clase cancelada."


def _token_payload(schedule: Schedule) -> dict:
    return {"schedule_id": str(schedule.id), "version": schedule.check_in_qr_version}


def generate_schedule_qr(schedule: Schedule) -> dict:
    token = signing.dumps(_token_payload(schedule), salt=QR_TOKEN_SALT, compress=True)
    query = urlencode({"token": token})
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    return {
        "schedule_id": str(schedule.id),
        "token": token,
        "url": f"{frontend_url}/#check-in/{schedule.id}?{query}",
        "valid_from": schedule.start_time - timedelta(minutes=15),
        "valid_until": schedule.start_time,
    }


@transaction.atomic
def regenerate_schedule_qr(schedule: Schedule) -> dict:
    schedule.check_in_qr_version += 1
    schedule.save(update_fields=["check_in_qr_version", "modified"])
    return generate_schedule_qr(schedule)


def validate_schedule_qr(schedule: Schedule, token: str) -> None:
    try:
        payload = signing.loads(token, salt=QR_TOKEN_SALT)
    except signing.BadSignature as exc:
        raise ReservationInvalidStateException(QR_INVALID_MESSAGE) from exc
    if payload != _token_payload(schedule):
        raise ReservationInvalidStateException(QR_INVALID_MESSAGE)
    if schedule.status == schedule_constants.SCHEDULE_STATUS_CANCELED:
        raise ReservationInvalidStateException(QR_CANCELLED_CLASS_MESSAGE)
    now = timezone.now()
    if now < schedule.start_time - timedelta(minutes=15) or now > schedule.start_time:
        raise ReservationInvalidStateException(MEMBER_CHECK_IN_WINDOW_MESSAGE)


@transaction.atomic
def check_in_member_by_qr(schedule_id: str, user_id: str, token: str) -> ReservationSchema:
    try:
        schedule = Schedule.objects.select_for_update().get(id=schedule_id, is_removed=False)
    except Schedule.DoesNotExist as exc:
        raise ReservationInvalidStateException(QR_INVALID_MESSAGE) from exc
    validate_schedule_qr(schedule, token)
    try:
        reservation = Reservation.objects.select_for_update().get(
            schedule=schedule,
            member__user_id=user_id,
            status=constants.RESERVATION_STATUS_RESERVED,
            is_removed=False,
        )
    except Reservation.DoesNotExist as exc:
        raise ReservationInvalidStateException(QR_NO_RESERVATION_MESSAGE) from exc
    checked_in = set_reservation_attendance(
        str(reservation.id), constants.RESERVATION_STATUS_ATTENDED, method="qr"
    )
    return ReservationSchema.model_validate(checked_in)
