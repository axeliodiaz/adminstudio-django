"""Services for schedules app (renamed from schedules).

Provide schema-based service functions that delegate to domain logic in schedules/schedules.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List
from uuid import UUID

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from apps.members import constants as member_constants
from apps.schedules import constants
from apps.schedules.models import Schedule
from apps.schedules.schedules import (
    create_schedule as create_schedule_model,
    delete_schedule as delete_schedule_model,
    get_schedule_by_id as get_schedule_by_id_domain,
    get_schedules_list,
    update_schedule as update_schedule_model,
)
from apps.schedules.schemas import AdminScheduleSchema, ScheduleSchema


def create_schedule(
    *,
    instructor_id: UUID,
    start_time: datetime,
    duration_minutes: int,
    room_id: UUID,
    status: str,
    title: str = "",
    description: str | None = None,
) -> ScheduleSchema:
    """Create a schedule and return a ScheduleSchema.

    Delegates the creation logic to apps.schedules.schedules.create_schedule.
    """
    schedule = create_schedule_model(
        instructor_id=instructor_id,
        start_time=start_time,
        duration_minutes=duration_minutes,
        room_id=room_id,
        status=status,
        title=title,
        description=description,
    )
    return ScheduleSchema.model_validate(schedule)


def to_schedule_schema_list(items: Iterable) -> List[ScheduleSchema]:
    """Convert iterable of Schedule model instances to a list of ScheduleSchema."""
    return [ScheduleSchema.model_validate(obj) for obj in items]


def get_schedule_schema_list(
    *,
    start_time: datetime | None = None,
    instructor_id: UUID | str | None = None,
    room_name: str | None = None,
) -> List[ScheduleSchema]:
    """Fetch schedules ordered by start_time and return as list of ScheduleSchema.

    If start_time is provided, filter schedules by start_time (>= provided). Optionally filter by instructor id and/or room name.
    """
    return to_schedule_schema_list(
        get_schedules_list(
            start_time=start_time,
            instructor_id=instructor_id,
            room_name=room_name,
        )
    )


def get_schedule_schema_by_id(schedule_id: UUID) -> ScheduleSchema:
    """Fetch schedule by id and return as ScheduleSchema.

    Delegates to apps.schedules.schedules.get_schedule_by_id.
    """
    schedule = get_schedule_by_id_domain(schedule_id)
    return ScheduleSchema.model_validate(schedule)


def _instructor_display_name(schedule: Schedule) -> str:
    user = getattr(schedule.instructor, "user", None)
    if not user:
        return ""
    name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return name or user.username or user.email or ""


def _serialize_admin_schedule(schedule: Schedule, *, copies_created: int | None = None) -> dict:
    room = schedule.room
    studio = getattr(room, "studio", None)
    payload = {
        "id": schedule.id,
        "title": schedule.title or "",
        "description": schedule.description,
        "created": schedule.created,
        "modified": schedule.modified,
        "instructor_id": schedule.instructor_id,
        "instructor_name": _instructor_display_name(schedule),
        "start_time": schedule.start_time,
        "duration_minutes": schedule.duration_minutes,
        "room_id": schedule.room_id,
        "room_name": room.name if room else "",
        "studio_id": studio.id if studio else None,
        "studio_name": studio.name if studio else None,
        "room_capacity": room.capacity if room else None,
        "reservation_count": (
            getattr(schedule, "reservation_count", None)
            if getattr(schedule, "reservation_count", None) is not None
            else schedule.reservations.filter(
                is_removed=False,
                status=member_constants.RESERVATION_STATUS_RESERVED,
            ).count()
        ),
        "status": schedule.status,
        "copies_created": copies_created,
    }
    return AdminScheduleSchema.model_validate(payload).model_dump(mode="json")


def _admin_queryset():
    return (
        Schedule.objects.select_related("instructor__user", "room__studio")
        .annotate(
            reservation_count=Count(
                "reservations",
                filter=Q(
                    reservations__is_removed=False,
                    reservations__status=member_constants.RESERVATION_STATUS_RESERVED,
                ),
            )
        )
        .order_by("start_time")
    )


def list_admin_schedules(
    *,
    search: str | None = None,
    status: str | None = None,
    instructor_id: str | UUID | None = None,
    room_id: str | UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[dict]:
    """Return non-deleted schedules for the staff admin calendar."""
    queryset = _admin_queryset()

    if status in constants.SCHEDULE_STATUSES:
        queryset = queryset.filter(status=status)
    if instructor_id:
        queryset = queryset.filter(instructor_id=instructor_id)
    if room_id:
        queryset = queryset.filter(room_id=room_id)
    if start_time is not None:
        queryset = queryset.filter(start_time__gte=start_time)
    if end_time is not None:
        queryset = queryset.filter(start_time__lte=end_time)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(room__name__icontains=term)
            | Q(room__studio__name__icontains=term)
            | Q(instructor__user__first_name__icontains=term)
            | Q(instructor__user__last_name__icontains=term)
            | Q(instructor__user__username__icontains=term)
        ).distinct()

    return [_serialize_admin_schedule(schedule) for schedule in queryset]


def get_admin_schedule(*, schedule_id: str | UUID) -> dict:
    schedule = get_object_or_404(_admin_queryset(), id=schedule_id)
    return _serialize_admin_schedule(schedule)


def _validate_schedule_write(*, data: dict, require_required_fields: bool) -> None:
    if require_required_fields:
        if not data.get("instructor_id"):
            raise ValueError("El instructor es obligatorio.")
        if not data.get("room_id"):
            raise ValueError("La sala es obligatoria.")
        if data.get("start_time") is None:
            raise ValueError("La fecha y hora de inicio son obligatorias.")
        if data.get("duration_minutes") is None:
            raise ValueError("La duración es obligatoria.")

    if "title" in data and data["title"] is not None and not str(data["title"]).strip():
        raise ValueError("El título no puede estar vacío.")

    if "duration_minutes" in data and data["duration_minutes"] is not None:
        if int(data["duration_minutes"]) <= 0:
            raise ValueError("La duración debe ser un número positivo.")

    if (
        "status" in data
        and data["status"] is not None
        and data["status"] not in constants.SCHEDULE_STATUSES
    ):
        raise ValueError("El estado de la clase es inválido.")

    if "repeat_weeks" in data and data["repeat_weeks"] is not None:
        weeks = int(data["repeat_weeks"])
        if weeks < 1 or weeks > 16:
            raise ValueError("repeat_weeks debe estar entre 1 y 16.")


def create_admin_schedule(*, data: dict) -> dict:
    """Create one class, optionally repeating it weekly."""
    _validate_schedule_write(data=data, require_required_fields=True)

    title = str(data.get("title") or "").strip()
    weeks = int(data.get("repeat_weeks") or 1)
    created: list[Schedule] = []
    start_time = data["start_time"]

    for offset in range(weeks):
        schedule = create_schedule_model(
            instructor_id=data["instructor_id"],
            start_time=start_time + timedelta(weeks=offset),
            duration_minutes=int(data["duration_minutes"]),
            room_id=data["room_id"],
            status=data.get("status") or constants.SCHEDULE_STATUS_SCHEDULED,
            title=title,
            description=data.get("description"),
        )
        created.append(schedule)

    first = get_object_or_404(_admin_queryset(), id=created[0].id)
    return _serialize_admin_schedule(first, copies_created=len(created))


def update_admin_schedule(*, schedule_id: str | UUID, data: dict) -> dict:
    _validate_schedule_write(data=data, require_required_fields=False)
    if "repeat_weeks" in data:
        data = {key: value for key, value in data.items() if key != "repeat_weeks"}

    schedule = get_object_or_404(Schedule, id=schedule_id)
    if "title" in data and data["title"] is not None:
        data["title"] = str(data["title"]).strip()

    update_schedule_model(schedule, data=data)
    return get_admin_schedule(schedule_id=schedule.id)


def delete_admin_schedule(*, schedule_id: str | UUID) -> None:
    schedule = get_object_or_404(_admin_queryset(), id=schedule_id)
    reserved = int(getattr(schedule, "reservation_count", 0) or 0)
    if reserved > 0:
        raise ValueError(
            "No se puede eliminar una clase con reservas activas. "
            "Cáncela la clase o reubica a los socios primero."
        )
    delete_schedule_model(schedule)
