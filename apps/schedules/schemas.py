import uuid
from datetime import datetime

from pydantic import BaseModel


class ScheduleSchema(BaseModel):
    id: uuid.UUID
    title: str = ""
    description: str | None = None
    created: datetime
    modified: datetime
    instructor_id: uuid.UUID
    start_time: datetime
    duration_minutes: int
    room_id: uuid.UUID
    status: str

    model_config = {"from_attributes": True}
