import uuid
from datetime import datetime

from pydantic import BaseModel

from apps.users.schemas import UserSchema


class MemberSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    user: UserSchema

    model_config = {"from_attributes": True}


class ReservationSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    member_id: uuid.UUID
    schedule_id: uuid.UUID
    status: str
    notes: str | None = None

    model_config = {"from_attributes": True}
