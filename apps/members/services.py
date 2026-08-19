from datetime import date
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from apps.members import members
from apps.members.models import Member, Reservation
from apps.members.schemas import (
    AdminMemberSchema,
    AdminReservationSchema,
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


def _member_display_name(user) -> str:
    if not user:
        return ""
    name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return name or user.username or user.email or ""


def _instructor_display_name(schedule) -> str:
    instructor = getattr(schedule, "instructor", None)
    user = getattr(instructor, "user", None) if instructor else None
    return _member_display_name(user)


def _serialize_admin_reservation(reservation: Reservation) -> dict:
    member = reservation.member
    user = getattr(member, "user", None)
    schedule = reservation.schedule
    room = getattr(schedule, "room", None)
    studio = getattr(room, "studio", None) if room else None

    payload = {
        "id": reservation.id,
        "created": reservation.created,
        "modified": reservation.modified,
        "member_id": reservation.member_id,
        "member_name": _member_display_name(user),
        "member_email": getattr(user, "email", "") or "",
        "user_id": getattr(user, "id", None),
        "schedule_id": reservation.schedule_id,
        "schedule_title": schedule.title or "",
        "schedule_start_time": schedule.start_time,
        "duration_minutes": schedule.duration_minutes,
        "instructor_id": schedule.instructor_id,
        "instructor_name": _instructor_display_name(schedule),
        "room_id": schedule.room_id,
        "room_name": room.name if room else "",
        "studio_id": studio.id if studio else None,
        "studio_name": studio.name if studio else None,
        "room_capacity": room.capacity if room else None,
        "status": reservation.status,
        "spot": reservation.spot,
        "notes": reservation.notes or "",
    }
    return AdminReservationSchema.model_validate(payload).model_dump(mode="json")


def _parse_date(value: str | None, field_name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be YYYY-MM-DD.") from exc


def list_admin_reservations(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    member_id: str | UUID | None = None,
    schedule_id: str | UUID | None = None,
    instructor_id: str | UUID | None = None,
    room_id: str | UUID | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """Return enriched reservations for the staff admin list."""
    parsed_start = (
        start_date if isinstance(start_date, date) else _parse_date(start_date, "start_date")
    )
    parsed_end = end_date if isinstance(end_date, date) else _parse_date(end_date, "end_date")

    if not schedule_id and (parsed_start is None or parsed_end is None):
        today = date.today()
        parsed_start = today.fromordinal(today.toordinal() - today.weekday())
        parsed_end = parsed_start.fromordinal(parsed_start.toordinal() + 6)

    qs = members.list_admin_reservations(
        start_date=parsed_start,
        end_date=parsed_end,
        member_id=member_id,
        schedule_id=schedule_id,
        instructor_id=instructor_id,
        room_id=room_id,
        status=status,
        search=search,
    )
    return [_serialize_admin_reservation(obj) for obj in qs]


def get_admin_reservation(reservation_id: str | UUID) -> dict:
    """Return one enriched reservation for the staff admin."""
    try:
        reservation = (
            Reservation.objects.select_related(
                "member__user",
                "schedule__instructor__user",
                "schedule__room__studio",
            )
            .filter(is_removed=False)
            .get(id=reservation_id)
        )
    except Reservation.DoesNotExist as exc:
        raise ValueError("Reservation not found.") from exc
    return _serialize_admin_reservation(reservation)


def create_admin_reservation(data: dict) -> dict:
    """Create a reservation for a given member/user from the staff admin."""
    user_id = data.get("user_id")
    member_id = data.get("member_id")

    if not user_id and not member_id:
        raise ValueError("user_id or member_id is required.")
    if user_id and member_id:
        raise ValueError("Provide either user_id or member_id, not both.")

    if member_id:
        try:
            member = Member.objects.select_related("user").get(id=member_id, is_removed=False)
        except Member.DoesNotExist as exc:
            raise ValueError("Member not found.") from exc
        user_id = member.user_id

    try:
        User.objects.get(id=user_id)
    except User.DoesNotExist as exc:
        raise ValueError("User not found.") from exc

    reservation = members.create_reservation(
        {
            "user_id": user_id,
            "schedule_id": data["schedule_id"],
            "spot": data["spot"],
            "notes": data.get("notes") or "Admin reservation",
        }
    )
    return get_admin_reservation(reservation.id)


def cancel_admin_reservation(reservation_id: str | UUID) -> dict:
    """Cancel a reservation from the staff admin."""
    try:
        members.cancel_reservation(str(reservation_id))
    except Reservation.DoesNotExist as exc:
        raise ValueError("Reservation not found.") from exc
    return get_admin_reservation(reservation_id)


def change_admin_reservation_spot(reservation_id: str | UUID, new_spot: int) -> dict:
    """Change the spot of a reservation from the staff admin."""
    try:
        members.change_reservation_spot_by_id(str(reservation_id), new_spot)
    except Reservation.DoesNotExist as exc:
        raise ValueError("Reservation not found.") from exc
    return get_admin_reservation(reservation_id)
