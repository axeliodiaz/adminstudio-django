from datetime import timedelta

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.members import constants
from apps.members.exceptions import (
    InvalidSpotException,
    RoomFullException,
    ReservationInvalidStateException,
)
from apps.members.models import Member, Reservation
from apps.schedules.schedules import get_schedule_by_id
from apps.studios.models import StudioSettings
from apps.users.services import get_or_create_user
from apps.verifications.services import create_verification_code

ADMIN_RESERVATION_STATUSES = {
    constants.RESERVATION_STATUS_RESERVED,
    constants.RESERVATION_STATUS_CANCELLED,
    constants.RESERVATION_STATUS_ATTENDED,
    constants.RESERVATION_STATUS_MISSED,
}

ATTENDANCE_INVALID_STATUS_MESSAGE = "Estado de asistencia inválido."
ATTENDANCE_CANCELLED_MESSAGE = "No se puede marcar asistencia de una reserva cancelada."
RESERVATION_NOT_FOUND_MESSAGE = "Reserva no encontrada."
SCHEDULE_NOT_FOUND_MESSAGE = "Clase no encontrada."


def set_reservation_attendance(reservation_id: str, status: str) -> Reservation:
    """Staff/coach attendance: RESERVED, ATTENDED or MISSED. Not allowed on cancelled bookings."""
    if status not in constants.ATTENDANCE_STATUSES:
        raise ReservationInvalidStateException(ATTENDANCE_INVALID_STATUS_MESSAGE)
    try:
        reservation = Reservation.objects.select_related(
            "member__user",
            "schedule__instructor__user",
            "schedule__room__studio",
        ).get(id=reservation_id, is_removed=False)
    except Reservation.DoesNotExist as exc:
        raise Reservation.DoesNotExist(RESERVATION_NOT_FOUND_MESSAGE) from exc
    if reservation.status == constants.RESERVATION_STATUS_CANCELLED:
        raise ReservationInvalidStateException(ATTENDANCE_CANCELLED_MESSAGE)
    if reservation.status == status:
        return reservation
    reservation.status = status
    reservation.save(update_fields=["status"])
    return reservation


def get_member_by_id(member_id: str) -> Member:
    """Get a Member by id."""
    return Member.objects.get(id=member_id)


def get_member_by_user_id(user_id: str) -> Member:
    """Get a Member by related User id."""
    return Member.objects.get(user_id=user_id)


def get_or_create_member_user(
    validated_data: dict, *, is_active: bool = True
) -> tuple[Member, bool]:
    """
    Domain logic for members: get or create Member linked to a User.

    Returns a tuple of (Member instance, created flag).
    Public registration should pass is_active=False so the account
    stays inactive until the email is confirmed.
    """
    payload = dict(validated_data)
    payload.setdefault("is_active", is_active)
    user = get_or_create_user(payload)
    member, created = Member.objects.get_or_create(user=user)
    if created or not user.is_active:
        create_verification_code(user=member.user)
    return member, created


def get_scheduled_reservations_by_member_id_and_schedule_id(
    member_id: str, schedule_id: str
) -> QuerySet[Reservation]:
    """Get all reservations for a member and schedule."""
    return Reservation.objects.filter(
        schedule_id=schedule_id, member_id=member_id, status=constants.RESERVATION_STATUS_RESERVED
    )


def create_reservation(validated_data: dict) -> Reservation:
    """Domain logic: create a Reservation for a member and schedule.

    Expects keys: user_id (UUID), schedule_id (UUID), spot (int), optional notes.
    Consumes one class credit unless the member has an unlimited membership.
    """
    # First, ensure the referenced user exists to avoid FK violations when creating Member
    from django.contrib.auth import get_user_model

    from apps.wallets.services import WalletService

    User = get_user_model()
    user = User.objects.get(id=validated_data["user_id"])  # may raise DoesNotExist

    # Ensure member exists for the given user; create if missing and trigger verification
    member, created = Member.objects.get_or_create(user=user)
    if created:
        create_verification_code(user=member.user)

    # Fetch Schedule model instance via domain function
    schedule = get_schedule_by_id(validated_data["schedule_id"])

    # Validate spot range
    spot = validated_data["spot"]
    room_capacity = schedule.room.capacity
    if spot < 1:
        raise InvalidSpotException("Spot must be greater than or equal to 1.")
    if spot > room_capacity:
        raise InvalidSpotException(
            f"Spot must be less than or equal to the room capacity ({room_capacity})."
        )

    existing_for_member = get_scheduled_reservations_by_member_id_and_schedule_id(
        member.id, schedule.id
    )
    if existing_for_member.exists():
        raise ReservationInvalidStateException("Ya tienes una reserva para esta clase.")

    with transaction.atomic():
        reserved_count = Reservation.objects.filter(
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            is_removed=False,
        ).count()
        if reserved_count >= room_capacity:
            raise RoomFullException("Room is full.")

        taken_spot = Reservation.objects.filter(
            schedule=schedule,
            spot=spot,
            status=constants.RESERVATION_STATUS_RESERVED,
            is_removed=False,
        ).exists()
        if taken_spot:
            raise InvalidSpotException(f"Spot {spot} is already taken.")

        credit_charged = WalletService.consume_class_credit(user)

        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            spot=spot,
            notes=validated_data.get("notes") or "",
            credit_charged=credit_charged,
        )

    from apps.members.notifications import send_reservation_confirmed_email

    send_reservation_confirmed_email(reservation)
    return reservation


def get_reservation_by_id(reservation_id: str) -> Reservation:
    """Get a Reservation by id."""
    return Reservation.objects.get(id=reservation_id)


def cancel_reservation(
    reservation_id: str,
    *,
    bypass_free_cancel_window: bool = False,
    cancellation_source: str = constants.CANCELLATION_SOURCE_MEMBER,
    cancellation_reason: str = "",
    promote_waitlist: bool | None = None,
    notify: bool | None = None,
) -> Reservation:
    """Cancel a reservation if it is currently in RESERVED status.

    Raises Reservation.DoesNotExist if the reservation does not exist.
    Raises ReservationInvalidStateException if the reservation is not in RESERVED status
    or the free-cancellation window has closed (unless bypassed for staff).

    Studio/schedule cancellations refund the credit (if charged) and notify the member.
    Member cancellations within the free window also refund.
    """
    from apps.wallets.services import WalletService

    reservation = get_reservation_by_id(reservation_id)
    if reservation.status != constants.RESERVATION_STATUS_RESERVED:
        raise ReservationInvalidStateException("Only RESERVED reservations can be cancelled.")
    if not bypass_free_cancel_window:
        hours = StudioSettings.load().free_cancellation_hours
        deadline = reservation.schedule.start_time - timedelta(hours=hours)
        if timezone.now() >= deadline:
            raise ReservationInvalidStateException(
                f"Cancelación gratuita solo hasta {hours} horas antes de la clase."
            )

    should_promote = (
        promote_waitlist
        if promote_waitlist is not None
        else cancellation_source != constants.CANCELLATION_SOURCE_SCHEDULE
    )
    should_notify = (
        notify
        if notify is not None
        else cancellation_source in constants.STUDIO_CANCELLATION_SOURCES
    )

    refunded = False
    with transaction.atomic():
        if reservation.credit_charged:
            WalletService.refund_class_credit(reservation.member.user)
            reservation.credit_charged = False
            refunded = True
        reservation.status = constants.RESERVATION_STATUS_CANCELLED
        reservation.cancellation_source = cancellation_source
        reservation.save(
            update_fields=["status", "cancellation_source", "credit_charged", "modified"]
        )

    if should_promote:
        from apps.members.waitlist import promote_waitlist_for_schedule

        promote_waitlist_for_schedule(reservation.schedule_id, reservation.spot)
        # A waitlisted member is offered first; alerts only happen when no priority claimant exists.
        from apps.members.alerts import notify_favorite_spot_available

        notify_favorite_spot_available(reservation.schedule, reservation.spot)

    if should_notify:
        from apps.members.notifications import send_class_cancelled_email

        reason = cancellation_reason
        if not reason and cancellation_source == constants.CANCELLATION_SOURCE_SCHEDULE:
            reason = getattr(reservation.schedule, "cancellation_reason", "") or ""
        send_class_cancelled_email(reservation, reason=reason, credit_refunded=refunded)

    return reservation


def change_reservation_spot(schedule_id: str, user_id: str, new_spot: int) -> Reservation:
    """Change the spot of an existing reservation atomically.

    This function:
    1. Finds the reservation for the given schedule and user
    2. Validates the reservation exists and is in RESERVED status
    3. Validates the new spot is available and valid
    4. Updates the spot in a single transaction

    Raises:
        Reservation.DoesNotExist: If reservation doesn't exist
        ReservationInvalidStateException: If reservation is not RESERVED
        InvalidSpotException: If new spot is invalid or unavailable
    """
    freed_spot = None
    with transaction.atomic():
        # Get member from user_id
        member = get_member_by_user_id(user_id)

        # Find the RESERVED reservation for this schedule and member
        reservation = Reservation.objects.filter(
            schedule_id=schedule_id,
            member=member,
            status=constants.RESERVATION_STATUS_RESERVED,
        ).first()

        # If no RESERVED reservation found, check if any reservation exists
        # to provide a more specific error message
        if not reservation:
            any_reservation = Reservation.objects.filter(
                schedule_id=schedule_id,
                member=member,
            ).first()

            if any_reservation:
                # Reservation exists but is not RESERVED
                raise ReservationInvalidStateException(
                    "Only RESERVED reservations can change spots."
                )
            else:
                # No reservation found at all
                raise Reservation.DoesNotExist(
                    f"Reservation not found for schedule {schedule_id} and user {user_id}"
                )

        schedule = reservation.schedule
        room_capacity = schedule.room.capacity

        # Validate spot range
        if new_spot < 1:
            raise InvalidSpotException("Spot must be greater than or equal to 1.")
        if new_spot > room_capacity:
            raise InvalidSpotException(
                f"Spot must be less than or equal to the room capacity ({room_capacity})."
            )

        # Check if new spot is already taken by another reservation
        existing_reservation = (
            Reservation.objects.filter(
                schedule=schedule, spot=new_spot, status=constants.RESERVATION_STATUS_RESERVED
            )
            .exclude(id=reservation.id)
            .first()
        )

        if existing_reservation:
            raise InvalidSpotException(f"Spot {new_spot} is already taken.")

        # Update the spot
        freed_spot = reservation.spot
        reservation.spot = new_spot
        reservation.save(update_fields=["spot", "modified"])

    from apps.members.waitlist import promote_waitlist_for_schedule
    from apps.members.alerts import notify_favorite_spot_available

    promote_waitlist_for_schedule(reservation.schedule_id, freed_spot)
    notify_favorite_spot_available(reservation.schedule, freed_spot)
    return reservation


def list_reservations_by_date_range(
    *,
    start_date=None,
    end_date=None,
    member_id=None,
    schedule_id=None,
    instructor_id=None,
    room_id=None,
) -> QuerySet[Reservation]:
    """
    Return reservations filtered by schedule start date range and optional filters.

    Uses __range for date filtering (inclusive) as requested.
    Can filter by schedule_id directly, or by date range with optional filters.
    Excludes cancelled reservations from the results.
    """
    filters = {}

    # If schedule_id is provided, filter by it directly
    if schedule_id is not None:
        filters["schedule_id"] = schedule_id
    # Otherwise, use date range if provided
    elif start_date is not None and end_date is not None:
        filters["schedule__start_time__date__range"] = (start_date, end_date)

    if member_id is not None:
        filters["member_id"] = member_id
    if instructor_id is not None:
        filters["schedule__instructor_id"] = instructor_id
    if room_id is not None:
        filters["schedule__room_id"] = room_id

    # Exclude member-cancelled reservations; keep studio/schedule cancellations visible
    # so Mis reservas can show "clase cancelada / crédito devuelto".
    return (
        Reservation.objects.filter(**filters)
        .exclude(
            Q(status=constants.RESERVATION_STATUS_CANCELLED)
            & ~Q(cancellation_source__in=constants.STUDIO_CANCELLATION_SOURCES)
        )
        .select_related("schedule")
    )


def list_admin_reservations(
    *,
    start_date=None,
    end_date=None,
    member_id=None,
    schedule_id=None,
    instructor_id=None,
    room_id=None,
    status=None,
    search=None,
) -> QuerySet[Reservation]:
    """
    Return reservations for the staff admin, including cancelled rows.

    Unlike the member-facing list, cancelled reservations are kept unless
    a specific status filter is applied.
    """
    filters = {"is_removed": False}

    if schedule_id is not None:
        filters["schedule_id"] = schedule_id
    elif start_date is not None and end_date is not None:
        filters["schedule__start_time__date__range"] = (start_date, end_date)

    if member_id is not None:
        filters["member_id"] = member_id
    if instructor_id is not None:
        filters["schedule__instructor_id"] = instructor_id
    if room_id is not None:
        filters["schedule__room_id"] = room_id
    if status in ADMIN_RESERVATION_STATUSES:
        filters["status"] = status

    queryset = Reservation.objects.filter(**filters).select_related(
        "member__user",
        "schedule__instructor__user",
        "schedule__room__studio",
    )

    if search:
        term = search.strip()
        if term:
            queryset = queryset.filter(
                Q(member__user__email__icontains=term)
                | Q(member__user__username__icontains=term)
                | Q(member__user__first_name__icontains=term)
                | Q(member__user__last_name__icontains=term)
                | Q(schedule__title__icontains=term)
            )

    return queryset.order_by("schedule__start_time", "spot", "created")


def change_reservation_spot_by_id(reservation_id: str, new_spot: int) -> Reservation:
    """Change spot for a reservation identified by its id."""
    reservation = get_reservation_by_id(reservation_id)
    return change_reservation_spot(
        str(reservation.schedule_id),
        str(reservation.member.user_id),
        new_spot,
    )
