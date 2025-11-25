from uuid import UUID

from apps.members import members
from apps.members.schemas import MemberSchema, ReservationSchema
from apps.users.services import get_or_create_user as _get_or_create_user


def get_or_create_user(validated_data: dict):
    """Re-export users service for backward compatibility in tests."""
    return _get_or_create_user(validated_data)


def get_member_from_user_id(user_id: str | UUID) -> MemberSchema:
    member = members.get_member_by_user_id(user_id)
    return MemberSchema.model_validate(member)


def get_or_create_member_user(validated_data: dict) -> tuple[MemberSchema, bool]:
    """
    Application service: delegates to domain logic (apps.members.members)
    and returns a Pydantic MemberSchema along with the created flag.
    """
    member, created = members.get_or_create_member_user(validated_data)
    return MemberSchema.model_validate(member), created


def create_reservation(validated_data: dict) -> ReservationSchema:
    """Application service: create reservation and return ReservationSchema."""
    reservation = members.create_reservation(validated_data)
    return ReservationSchema.model_validate(reservation)


def cancel_reservation(reservation_id: str) -> ReservationSchema:
    """Application service: cancel reservation and return ReservationSchema."""
    reservation = members.cancel_reservation(reservation_id)
    return ReservationSchema.model_validate(reservation)


def list_reservations(validated_query: dict) -> list[ReservationSchema]:
    """Application service: list reservations via domain and return schemas."""
    # Map serializer field names to function parameter names
    query_params = {}
    if "start_date" in validated_query:
        query_params["start_date"] = validated_query["start_date"]
    if "end_date" in validated_query:
        query_params["end_date"] = validated_query["end_date"]
    if "member_id" in validated_query:
        query_params["member_id"] = validated_query["member_id"]
    if "schedule_id" in validated_query:
        query_params["schedule_id"] = validated_query["schedule_id"]
    if "schedule__instructor_id" in validated_query:
        query_params["instructor_id"] = validated_query["schedule__instructor_id"]
    if "schedule__room_id" in validated_query:
        query_params["room_id"] = validated_query["schedule__room_id"]

    qs = members.list_reservations_by_date_range(**query_params)
    return [ReservationSchema.model_validate(obj) for obj in qs]
