"""Services for schedules app (renamed from schedules).

Provide schema-based service functions that delegate to domain logic in schedules/schedules.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List
from uuid import UUID

from apps.schedules.models import Schedule
from apps.schedules.schedules import create_schedule as create_schedule_model
from apps.schedules.schedules import get_schedules_list
from apps.schedules.schemas import ScheduleSchema


def create_schedule(
    *,
    instructor_id: UUID,
    start_time: datetime,
    duration_minutes: int,
    room_id: UUID,
    status: str,
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
    )
    return ScheduleSchema.model_validate(schedule)


def to_schedule_schema_list(items: Iterable) -> List[ScheduleSchema]:
    """Convert iterable of Schedule model instances to a list of ScheduleSchema."""
    return [ScheduleSchema.model_validate(obj) for obj in items]


def get_schedule_schema_list(
    *,
    start_time: datetime | None = None,
    instructor_username: str | None = None,
    room_name: str | None = None,
) -> List[ScheduleSchema]:
    """Fetch schedules ordered by start_time and return as list of ScheduleSchema.

    If start_time is provided, filter schedules by start_time (>= provided). Optionally filter by instructor username and/or room name.
    """
    return to_schedule_schema_list(
        get_schedules_list(
            start_time=start_time, instructor_username=instructor_username, room_name=room_name
        )
    )


def get_schedule_schema_by_id(schedule_id: UUID) -> ScheduleSchema:
    """Fetch schedule by id and return as ScheduleSchema."""
    return ScheduleSchema.model_validate(Schedule.objects.get(pk=schedule_id))
