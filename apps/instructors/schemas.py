import uuid
from datetime import datetime

from pydantic import BaseModel

from apps.users.schemas import UserSchema


class InstructorSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    user: UserSchema

    model_config = {"from_attributes": True}
