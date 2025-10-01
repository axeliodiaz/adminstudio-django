import uuid
from datetime import datetime

from pydantic import BaseModel


class InstructorSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    user_id: uuid.UUID

    model_config = {"from_attributes": True}
