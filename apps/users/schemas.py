from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None

    model_config = {"from_attributes": True}


class CurrentUserSchema(UserSchema):
    """Authenticated user payload for login and GET /api/auth/me/."""

    id: UUID | None = None
    is_staff: bool = False
    is_superuser: bool = False


class AdminUserSchema(BaseModel):
    """User row for the staff admin list and detail."""

    id: UUID
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    gender: str | None = None
    is_staff: bool = False
    is_superuser: bool = False
    is_active: bool = True
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class AdminUserUpdateSchema(BaseModel):
    """Partial payload for staff user edits. is_superuser is not writable."""

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    gender: str | None = None
    is_staff: bool | None = None
    is_active: bool | None = None


class UserPublicSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None

    model_config = {"from_attributes": True}


class UserProfileSchema(BaseModel):
    """
    Schema para exponer/actualizar datos de perfil del usuario.
    Vive en apps.users pero será usado por el endpoint de profiles.
    """

    username: str | None = None
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None
    birthdate: date | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    shoe_size: float | None = None
    phone_number: str | None = None
    address: str | None = None

    model_config = {"from_attributes": True}


class PersonalInfoSchema(BaseModel):
    """Información personal del usuario."""

    username: str | None = None
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None
    birthdate: date | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    phone_number: str | None = None
    address: str | None = None

    model_config = {"from_attributes": True}


class CyclingSchema(BaseModel):
    """Configuración de bicicleta y zapatillas de ciclismo."""

    seat_height: int | None = None
    seat_distance: int | None = None
    handlebar_distance: int | None = None
    cycling_shoe_size: float | None = None

    model_config = {"from_attributes": True}


class PreferencesSchema(BaseModel):
    """Preferencias de notificaciones y lista de espera."""

    waitlist_auto_confirm: bool = False

    model_config = {"from_attributes": True}


class UserProfileResponseSchema(BaseModel):
    """Schema estructurado por categorías para la respuesta del endpoint."""

    personal_info: PersonalInfoSchema
    cycling: CyclingSchema
    preferences: PreferencesSchema

    @classmethod
    def from_user(cls, user):
        return cls(
            personal_info=PersonalInfoSchema.model_validate(user),
            cycling=CyclingSchema.model_validate(user),
            preferences=PreferencesSchema.model_validate(user),
        )
