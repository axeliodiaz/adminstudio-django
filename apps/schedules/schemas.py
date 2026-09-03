import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ScheduleSchema(BaseModel):
    id: uuid.UUID
    title: str = ""
    description: str | None = None
    created: datetime
    modified: datetime
    instructor_id: uuid.UUID
    instructor_name: str = ""
    start_time: datetime
    duration_minutes: int
    room_id: uuid.UUID
    room_name: str = ""
    studio_id: uuid.UUID | None = None
    studio_name: str | None = None
    studio_address: str | None = None
    status: str
    capacity: int | None = None
    booked_count: int = 0
    waitlist_count: int = 0
    is_full: bool = False

    model_config = {"from_attributes": True}


class SubstitutionHistorySchema(BaseModel):
    id: uuid.UUID
    old_instructor_id: uuid.UUID
    old_instructor_name: str = ""
    new_instructor_id: uuid.UUID
    new_instructor_name: str = ""
    changed_by_id: uuid.UUID | None = None
    changed_by_name: str = ""
    changed_at: datetime
    reason: str = ""
    notify: bool = True
    reserved_notified: int = 0
    waitlist_notified: int = 0

    model_config = {"from_attributes": True}


class AdminScheduleSchema(BaseModel):
    """Schedule row for the PulseFit staff admin calendar."""

    id: uuid.UUID
    title: str = ""
    description: str | None = None
    created: datetime
    modified: datetime
    instructor_id: uuid.UUID
    instructor_name: str = ""
    start_time: datetime
    duration_minutes: int
    room_id: uuid.UUID
    room_name: str = ""
    studio_id: uuid.UUID | None = None
    studio_name: str | None = None
    room_capacity: int | None = None
    reservation_count: int = 0
    waitlist_count: int = 0
    status: str
    cancellation_reason: str = ""
    copies_created: int | None = None
    substitutions: list[SubstitutionHistorySchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SubstituteCoachWriteSchema(BaseModel):
    new_instructor_id: uuid.UUID
    reason: str | None = None
    notify: bool = True


class AdminScheduleWriteSchema(BaseModel):
    """Create or update payload for a class schedule from the staff admin."""

    title: str | None = None
    description: str | None = None
    instructor_id: uuid.UUID | None = None
    start_time: datetime | None = None
    duration_minutes: int | None = None
    room_id: uuid.UUID | None = None
    status: str | None = None
    cancellation_reason: str | None = None
    repeat_weeks: int | None = Field(default=None, ge=1, le=16)
