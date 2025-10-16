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


def create_reservation(validated_data: dict) -> Reservation:
    """Domain logic: create a Reservation for a member and schedule.

    Expects keys: user_id (UUID), schedule_id (UUID), optional notes.
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

    reservation = Reservation.objects.create(
        member=member,
        schedule=schedule,
        notes=validated_data.get("notes") or "",
    )
    return reservation
