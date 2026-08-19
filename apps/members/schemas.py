import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from apps.users.schemas import UserSchema


class MemberSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    user: UserSchema

    model_config = {"from_attributes": True}


class AdminMemberSchema(BaseModel):
    """Flattened member row for the PulseFit staff admin."""

    id: uuid.UUID
    user_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    username: str | None = None
    gender: str | None = None
    is_active: bool = True
    last_login: datetime | None = None
    class_credits: int = 0
    reservation_count: int = 0
    created: datetime
    modified: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_member(cls, member, *, reservation_count: int | None = None) -> "AdminMemberSchema":
        user = member.user
        wallet = getattr(user, "wallet", None)
        count = reservation_count
        if count is None:
            count = getattr(member, "reservation_count", None)
        if count is None:
            count = member.reservations.count()
        return cls(
            id=member.id,
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone_number=getattr(user, "phone_number", None),
            username=user.username,
            gender=getattr(user, "gender", None) or None,
            is_active=bool(user.is_active),
            last_login=user.last_login,
            class_credits=int(getattr(wallet, "class_credits", 0) or 0),
            reservation_count=int(count or 0),
            created=member.created,
            modified=member.modified,
        )


class AdminMemberUpdateSchema(BaseModel):
    """Partial payload for staff member edits."""

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    gender: Optional[str] = None
    is_active: bool | None = None


class AdminMemberCreateSchema(BaseModel):
    """Payload to register a member from the staff admin."""

    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone_number: str
    gender: Optional[str] = None


class ReservationSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    member_id: uuid.UUID
    schedule_id: uuid.UUID
    status: str
    spot: int | None = None

    model_config = {"from_attributes": True}
