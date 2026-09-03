from __future__ import annotations

from datetime import datetime
from typing import Iterable
from uuid import UUID

from django.db.models import Q

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
    end_time: datetime | None = None,
    instructor_id: UUID | str | None = None,
    instructor_ids: Iterable[UUID | str] | None = None,
    instructor_username: str | None = None,
    room_name: str | None = None,
    room_id: UUID | str | None = None,
    room_ids: Iterable[UUID | str] | None = None,
    title: str | None = None,
    titles: Iterable[str] | None = None,
    scheduled_only: bool = False,
):
    """Return queryset of schedules ordered by start_time.

    Filters are combined with AND. ``titles`` matches if the schedule title
    contains any of the given strings (case-insensitive).
    """
    qs = Schedule.objects.select_related(
        "instructor__user",
        "room__studio__address",
    ).filter(is_removed=False)
    if scheduled_only:
        qs = qs.filter(status=constants.SCHEDULE_STATUS_SCHEDULED)
    if start_time is not None:
        qs = qs.filter(start_time__gte=start_time)
    if end_time is not None:
        qs = qs.filter(start_time__lte=end_time)

    instructor_keys = [str(value) for value in (instructor_ids or []) if value]
    if instructor_id:
        instructor_keys.append(str(instructor_id))
    instructor_keys = list(dict.fromkeys(instructor_keys))
    if len(instructor_keys) == 1:
        qs = qs.filter(instructor_id=instructor_keys[0])
    elif instructor_keys:
        qs = qs.filter(instructor_id__in=instructor_keys)

    if instructor_username:
        qs = qs.filter(instructor__user__username__icontains=instructor_username)
    if room_name:
        qs = qs.filter(room__name__icontains=room_name)

    room_keys = [str(value) for value in (room_ids or []) if value]
    if room_id:
        room_keys.append(str(room_id))
    room_keys = list(dict.fromkeys(room_keys))
    if len(room_keys) == 1:
        qs = qs.filter(room_id=room_keys[0])
    elif room_keys:
        qs = qs.filter(room_id__in=room_keys)

    title_terms = [str(value).strip() for value in (titles or []) if str(value).strip()]
    if title and title.strip():
        title_terms.append(title.strip())
    title_terms = list(dict.fromkeys(title_terms))
    if len(title_terms) == 1:
        qs = qs.filter(title__icontains=title_terms[0])
    elif title_terms:
        title_query = Q()
        for term in title_terms:
            title_query |= Q(title__icontains=term)
        qs = qs.filter(title_query)

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
    if status == constants.SCHEDULE_STATUS_SCHEDULED:
        from apps.members.alerts import notify_schedule_available

        notify_schedule_available(schedule)

    return schedule


def update_schedule(schedule: Schedule, *, data: dict) -> Schedule:
    """Apply staff-editable fields onto an existing schedule."""
    if "status" in data and data["status"] not in constants.SCHEDULE_STATUSES:
        raise ValueError("Invalid schedule status.")
    if "duration_minutes" in data and data["duration_minutes"] is not None:
        if int(data["duration_minutes"]) <= 0:
            raise ValueError("duration_minutes must be a positive integer.")

    dirty: list[str] = []
    was_scheduled = schedule.status == constants.SCHEDULE_STATUS_SCHEDULED

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
        if not was_scheduled and schedule.status == constants.SCHEDULE_STATUS_SCHEDULED:
            from apps.members.alerts import notify_schedule_available

            notify_schedule_available(schedule)
    return schedule


def delete_schedule(schedule: Schedule) -> None:
    """Soft-delete a schedule."""
    schedule.delete()
