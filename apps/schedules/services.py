"""Services for schedules app (renamed from schedules).

Provide schema-based service functions that delegate to domain logic in schedules/schedules.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List
from uuid import UUID

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from apps.members.models import Reservation, WaitlistEntry
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


def _annotate_occupancy(queryset):
    """Attach booked/waitlist counts in two aggregated queries instead of per row."""
    return queryset.annotate(
        booked_count=Count(
            "reservations",
            filter=Q(
                reservations__is_removed=False,
                reservations__status=member_constants.RESERVATION_STATUS_RESERVED,
            ),
            distinct=True,
        ),
        waitlist_count=Count(
            "waitlist_entries",
            filter=Q(
                waitlist_entries__is_removed=False,
                waitlist_entries__status__in=member_constants.WAITLIST_ACTIVE_STATUSES,
            ),
            distinct=True,
        ),
    )


def _studio_address(schedule: Schedule) -> str | None:
    room = getattr(schedule, "room", None)
    studio = getattr(room, "studio", None) if room else None
    address = getattr(studio, "address", None) if studio else None
    value = getattr(address, "address", None) if address else None
    return value or None


def _schedule_display_fields(schedule: Schedule) -> dict:
    room = getattr(schedule, "room", None)
    studio = getattr(room, "studio", None) if room else None
    return {
        "instructor_name": _instructor_display_name(schedule),
        "room_name": room.name if room else "",
        "studio_id": studio.id if studio else None,
        "studio_name": studio.name if studio else None,
        "studio_address": _studio_address(schedule),
    }


def _schedule_occupancy(schedule: Schedule) -> dict:
    room = getattr(schedule, "room", None)
    capacity = room.capacity if room else None
    booked = getattr(schedule, "booked_count", None)
    if booked is None:
        booked = Reservation.objects.filter(
            schedule_id=schedule.id,
            status=member_constants.RESERVATION_STATUS_RESERVED,
            is_removed=False,
        ).count()
    waitlist_count = getattr(schedule, "waitlist_count", None)
    if waitlist_count is None:
        waitlist_count = WaitlistEntry.objects.filter(
            schedule_id=schedule.id,
            is_removed=False,
            status__in=member_constants.WAITLIST_ACTIVE_STATUSES,
        ).count()
    return {
        "capacity": capacity,
        "booked_count": booked,
        "waitlist_count": waitlist_count,
        "is_full": bool(capacity is not None and booked >= capacity),
        **_schedule_display_fields(schedule),
    }


def to_schedule_schema_list(items: Iterable) -> List[ScheduleSchema]:
    """Convert iterable of Schedule model instances to a list of ScheduleSchema."""
    if hasattr(items, "annotate"):
        items = _annotate_occupancy(items)
    schemas = []
    for obj in items:
        schema = ScheduleSchema.model_validate(obj)
        schemas.append(schema.model_copy(update=_schedule_occupancy(obj)))
    return schemas


def get_schedule_schema_list(
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    instructor_id: UUID | str | None = None,
    instructor_ids: Iterable[UUID | str] | None = None,
    room_name: str | None = None,
    room_id: UUID | str | None = None,
    room_ids: Iterable[UUID | str] | None = None,
    title: str | None = None,
    titles: Iterable[str] | None = None,
) -> List[ScheduleSchema]:
    """Fetch schedules ordered by start_time and return as list of ScheduleSchema."""
    return to_schedule_schema_list(
        get_schedules_list(
            start_time=start_time,
            end_time=end_time,
            instructor_id=instructor_id,
            instructor_ids=instructor_ids,
            room_name=room_name,
            room_id=room_id,
            room_ids=room_ids,
            title=title,
            titles=titles,
        )
    )


def get_schedule_schema_by_id(schedule_id: UUID) -> ScheduleSchema:
    """Fetch schedule by id and return as ScheduleSchema.

    Delegates to apps.schedules.schedules.get_schedule_by_id.
    """
    schedule = get_schedule_by_id_domain(schedule_id)
    schema = ScheduleSchema.model_validate(schedule)
    return schema.model_copy(update=_schedule_occupancy(schedule))


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
        "cancellation_reason": schedule.cancellation_reason or "",
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

    new_status = data.get("status")
    transitioning_to_canceled = (
        new_status == constants.SCHEDULE_STATUS_CANCELED
        and schedule.status != constants.SCHEDULE_STATUS_CANCELED
    )
    if transitioning_to_canceled:
        reason = data.get("cancellation_reason")
        if reason is None:
            reason = schedule.cancellation_reason or ""
        return cancel_admin_schedule(schedule_id=schedule.id, reason=str(reason or ""))

    update_schedule_model(schedule, data=data)
    return get_admin_schedule(schedule_id=schedule.id)


def cancel_admin_schedule(*, schedule_id: str | UUID, reason: str = "") -> dict:
    """Cancel a class: cascade to reservations (refund + email) and expire waitlist."""
    from apps.members.members import cancel_reservation
    from apps.members.waitlist import expire_waitlist_for_cancelled_schedule

    with transaction.atomic():
        schedule = get_object_or_404(
            Schedule.objects.select_for_update(), id=schedule_id, is_removed=False
        )
        if schedule.status != constants.SCHEDULE_STATUS_CANCELED:
            schedule.status = constants.SCHEDULE_STATUS_CANCELED
            schedule.cancellation_reason = (reason or "").strip()
            schedule.save(update_fields=["status", "cancellation_reason", "modified"])
        elif reason is not None and (reason or "").strip() != (schedule.cancellation_reason or ""):
            schedule.cancellation_reason = (reason or "").strip()
            schedule.save(update_fields=["cancellation_reason", "modified"])

        reserved_ids = list(
            Reservation.objects.filter(
                schedule_id=schedule.id,
                status=member_constants.RESERVATION_STATUS_RESERVED,
                is_removed=False,
            ).values_list("id", flat=True)
        )

    for reservation_id in reserved_ids:
        cancel_reservation(
            str(reservation_id),
            bypass_free_cancel_window=True,
            cancellation_source=member_constants.CANCELLATION_SOURCE_SCHEDULE,
            cancellation_reason=schedule.cancellation_reason,
            promote_waitlist=False,
        )

    expire_waitlist_for_cancelled_schedule(schedule.id)
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
