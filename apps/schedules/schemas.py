import uuid
from datetime import datetime

from pydantic import BaseModel


class ScheduleSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    instructor_id: uuid.UUID
    start_time: datetime
    duration_minutes: int
    room_id: uuid.UUID
    status: str

    model_config = {"from_attributes": True}
