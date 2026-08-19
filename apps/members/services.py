from uuid import UUID

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from apps.members import members
from apps.members.models import Member
from apps.members.schemas import (
    AdminMemberSchema,
    MemberSchema,
    ReservationSchema,
)
from apps.users.services import get_or_create_user as _get_or_create_user

User = get_user_model()

USER_ADMIN_FIELDS = {"first_name", "last_name", "email", "phone_number", "gender", "is_active"}
GENDER_VALUES = {"", "female", "male", "other"}


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


def _admin_member_dict(member: Member) -> dict:
    return AdminMemberSchema.from_member(member).model_dump(mode="json")


def list_admin_members(
    *,
    search: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """Return members for the staff admin list."""
    queryset = (
        Member.objects.select_related("user", "user__wallet")
        .annotate(reservation_count=Count("reservations"))
        .order_by("user__first_name", "user__last_name", "user__email")
    )

    if status == "active":
        queryset = queryset.filter(user__is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(user__is_active=False)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(user__first_name__icontains=term)
            | Q(user__last_name__icontains=term)
            | Q(user__email__icontains=term)
            | Q(user__username__icontains=term)
            | Q(user__phone_number__icontains=term)
        )

    return [_admin_member_dict(member) for member in queryset]


def get_admin_member(*, member_id: str | UUID) -> dict:
    """Return one member for the staff admin."""
    member = get_object_or_404(
        Member.objects.select_related("user", "user__wallet").annotate(
            reservation_count=Count("reservations")
        ),
        id=member_id,
    )
    return _admin_member_dict(member)


def _apply_admin_member_fields(member: Member, data: dict) -> Member:
    user = member.user
    user_dirty: list[str] = []
    sync_username = bool(user.username) and user.username == (user.email or "")

    if "gender" in data and data["gender"] is not None and data["gender"] not in GENDER_VALUES:
        raise ValueError("Género inválido.")

    if "email" in data:
        email = (data["email"] or "").strip()
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        taken = (
            User.objects.filter(is_removed=False)
            .filter(Q(email__iexact=email) | Q(username__iexact=email))
            .exclude(id=user.id)
            .exists()
        )
        if taken:
            raise ValueError("Ya existe un usuario con ese correo.")

    for field, value in data.items():
        if field not in USER_ADMIN_FIELDS:
            continue
        if field == "email":
            value = (value or "").strip()
            if sync_username:
                user.username = value
                user_dirty.append("username")
        elif field in {"first_name", "last_name", "phone_number", "gender"} and value is None:
            value = ""
        setattr(user, field, value)
        user_dirty.append(field)

    if user_dirty:
        user.save(update_fields=list(dict.fromkeys(user_dirty)))

    return member


def update_admin_member(*, member_id: str | UUID, data: dict) -> dict:
    """Update staff-editable member user fields."""
    member = get_object_or_404(
        Member.objects.select_related("user", "user__wallet"),
        id=member_id,
    )
    member = _apply_admin_member_fields(member, data)
    member = get_object_or_404(
        Member.objects.select_related("user", "user__wallet").annotate(
            reservation_count=Count("reservations")
        ),
        id=member_id,
    )
    return _admin_member_dict(member)


def create_admin_member(*, data: dict) -> tuple[dict, bool]:
    """Create (or fetch) a member from the staff admin and return the admin payload."""
    payload = dict(data)
    gender = payload.pop("gender", None)
    member_schema, created = get_or_create_member_user(payload)
    member = get_object_or_404(
        Member.objects.select_related("user", "user__wallet").annotate(
            reservation_count=Count("reservations")
        ),
        id=member_schema.id,
    )
    if gender is not None and created:
        member = _apply_admin_member_fields(member, {"gender": gender})
        member = get_object_or_404(
            Member.objects.select_related("user", "user__wallet").annotate(
                reservation_count=Count("reservations")
            ),
            id=member.id,
        )
    return _admin_member_dict(member), created


def create_reservation(validated_data: dict) -> ReservationSchema:
    """Application service: create reservation and return ReservationSchema."""
    reservation = members.create_reservation(validated_data)
    return ReservationSchema.model_validate(reservation)


def cancel_reservation(reservation_id: str) -> ReservationSchema:
    """Application service: cancel reservation and return ReservationSchema."""
    reservation = members.cancel_reservation(reservation_id)
    return ReservationSchema.model_validate(reservation)


def change_reservation_spot(schedule_id: str, user_id: str, new_spot: int) -> ReservationSchema:
    """Application service: change reservation spot and return ReservationSchema."""
    reservation = members.change_reservation_spot(schedule_id, user_id, new_spot)
    return ReservationSchema.model_validate(reservation)


def list_reservations(validated_query: dict) -> list[ReservationSchema]:
    """Application service: list reservations via domain and return schemas."""
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
