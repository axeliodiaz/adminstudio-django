from django.db import transaction
from django.db.models import QuerySet

from apps.members import constants
from apps.members.exceptions import (
    InvalidSpotException,
    RoomFullException,
    ReservationInvalidStateException,
)
from apps.members.models import Member, Reservation
from apps.schedules.schedules import get_schedule_by_id
from apps.users.services import get_or_create_user
from apps.verifications.services import create_verification_code


def get_member_by_id(member_id: str) -> Member:
    """Get a Member by id."""
    return Member.objects.get(id=member_id)


def get_member_by_user_id(user_id: str) -> Member:
    """Get a Member by related User id."""
    return Member.objects.get(user_id=user_id)


def get_or_create_member_user(validated_data: dict) -> tuple[Member, bool]:
    """
    Domain logic for members: get or create Member linked to a User.

    Returns a tuple of (Member instance, created flag).
    """
    user = get_or_create_user(validated_data)
    member, created = Member.objects.get_or_create(user=user)
    if created:
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
    """
    # First, ensure the referenced user exists to avoid FK violations when creating Member
    from django.contrib.auth import get_user_model

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

    members_in_schedule = get_scheduled_reservations_by_member_id_and_schedule_id(
        member.id, schedule.id
    )

    if members_in_schedule.count() > schedule.room.capacity:
        raise RoomFullException("Room is full.")

    reservation = Reservation.objects.create(
        member=member,
        schedule=schedule,
        spot=spot,
        notes=validated_data.get("notes") or "",
    )
    return reservation


def get_reservation_by_id(reservation_id: str) -> Reservation:
    """Get a Reservation by id."""
    return Reservation.objects.get(id=reservation_id)


def cancel_reservation(reservation_id: str) -> Reservation:
    """Cancel a reservation if it is currently in RESERVED status.

    Raises Reservation.DoesNotExist if the reservation does not exist.
    Raises ReservationInvalidStateException if the reservation is not in RESERVED status.
    """
    reservation = get_reservation_by_id(reservation_id)
    if reservation.status != constants.RESERVATION_STATUS_RESERVED:
        raise ReservationInvalidStateException("Only RESERVED reservations can be cancelled.")
    reservation.status = constants.RESERVATION_STATUS_CANCELLED
    reservation.save(update_fields=["status", "modified"])
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
    with transaction.atomic():
        # Get member from user_id
        member = get_member_by_user_id(user_id)

        # Find the reservation for this schedule and member (without status filter first)
        reservation = Reservation.objects.filter(
            schedule_id=schedule_id,
            member=member,
        ).first()

        if not reservation:
            raise Reservation.DoesNotExist(
                f"Reservation not found for schedule {schedule_id} and user {user_id}"
            )

        # Validate reservation is in RESERVED status
        if reservation.status != constants.RESERVATION_STATUS_RESERVED:
            raise ReservationInvalidStateException("Only RESERVED reservations can change spots.")

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
        reservation.spot = new_spot
        reservation.save(update_fields=["spot", "modified"])

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
    return Reservation.objects.filter(**filters)
