from pydantic import BaseModel, EmailStr


class UserSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None

    model_config = {"from_attributes": True}
