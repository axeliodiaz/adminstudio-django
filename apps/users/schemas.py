from pydantic import BaseModel, EmailStr


class UserSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    phone_number: str

    model_config = {"from_attributes": True}
