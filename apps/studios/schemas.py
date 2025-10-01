import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RoomSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    name: str
    capacity: int
    is_active: bool
    studio_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class StudioSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    name: str
    address: str
    is_active: bool
    rooms: list[RoomSchema] | None = Field(default=None, alias="rooms_list")

    model_config = {"from_attributes": True}
