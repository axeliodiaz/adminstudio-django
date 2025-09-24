import uuid

from pydantic import BaseModel, EmailStr


class Recipient(BaseModel):
    email: EmailStr
    name: str | None = None


class Notification(BaseModel):
    id: uuid.UUID
    subject: str
    message: str
    user_id: uuid.UUID
