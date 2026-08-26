from __future__ import annotations

from datetime import datetime
from uuid import UUID

from apps.instructors.services import get_instructor_by_id
from apps.schedules import constants
from apps.schedules.models import Schedule
from apps.studios.services import get_room as get_room_by_id


def get_schedule_by_id(schedule_id: UUID | str) -> Schedule:
    """Return a Schedule by id or 404."""
    return Schedule.objects.get(id=schedule_id)


def get_schedules_list(
    *,
    start_time: datetime | None = None,
    instructor_id: UUID | str | None = None,
    instructor_username: str | None = None,
    room_name: str | None = None,
):
    """Return queryset of schedules ordered by start_time.

    Optionally filter by start_time (>= provided value), by instructor id or instructor username,
    and/or by room name when provided.
    This helper replaces direct usages of Schedule.objects.all().order_by("start_time").
    """
    qs = Schedule.objects.select_related("room")
    if start_time is not None:
        qs = qs.filter(start_time__gte=start_time)
    if instructor_id:
        qs = qs.filter(instructor_id=instructor_id)
    if instructor_username:
        qs = qs.filter(instructor__user__username__icontains=instructor_username)
    if room_name:
        qs = qs.filter(room__name__icontains=room_name)
    return qs.order_by("start_time")


def create_schedule(
    *,
    instructor_id: UUID,
    start_time: datetime,
    duration_minutes: int,
    room_id: UUID,
    status: str,
    title: str = "",
    description: str | None = None,
) -> Schedule:
    """Create and return a Schedule model instance.

    Raises
    - ValueError: If the status value is invalid or duration is non-positive.
    - ObjectDoesNotExist: If the referenced Instructor or Room does not exist.
    """
    if status not in constants.SCHEDULE_STATUSES:
        raise ValueError("Invalid schedule status.")
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be a positive integer.")

    # Validate instructor existence using service (returns schema dict)
    _ = get_instructor_by_id(instructor_id)

    # Validate room existence using service (returns schema object)
    _ = get_room_by_id(room_id)

    schedule = Schedule.objects.create(
        title=title or "",
        description=description,
        instructor_id=instructor_id,
        start_time=start_time,
        duration_minutes=duration_minutes,
        room_id=room_id,
        status=status,
    )

    return schedule


def update_schedule(schedule: Schedule, *, data: dict) -> Schedule:
    """Apply staff-editable fields onto an existing schedule."""
    if "status" in data and data["status"] not in constants.SCHEDULE_STATUSES:
        raise ValueError("Invalid schedule status.")
    if "duration_minutes" in data and data["duration_minutes"] is not None:
        if int(data["duration_minutes"]) <= 0:
            raise ValueError("duration_minutes must be a positive integer.")

    dirty: list[str] = []

    if "instructor_id" in data and data["instructor_id"] is not None:
        get_instructor_by_id(data["instructor_id"])
        schedule.instructor_id = data["instructor_id"]
        dirty.append("instructor_id")

    if "room_id" in data and data["room_id"] is not None:
        get_room_by_id(data["room_id"])
        schedule.room_id = data["room_id"]
        dirty.append("room_id")

    for field in (
        "title",
        "description",
        "start_time",
        "duration_minutes",
        "status",
        "cancellation_reason",
    ):
        if field in data:
            setattr(schedule, field, data[field])
            dirty.append(field)

    if dirty:
        schedule.save(update_fields=[*dirty, "modified"])
    return schedule


def delete_schedule(schedule: Schedule) -> None:
    """Soft-delete a schedule."""
    schedule.delete()
