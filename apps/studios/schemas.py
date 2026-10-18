import uuid
from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from apps.studios.branding import (
    BrandingError,
    sanitize_svg,
    validate_font,
    validate_hex_color,
)


class RoomSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    name: str
    capacity: int
    is_active: bool
    studio_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class AddressSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}


class StudioSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    name: str
    address: Optional[AddressSchema] = None  # Full Address object
    is_active: bool
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    rooms: list[RoomSchema] | None = Field(default=None, alias="rooms_list")

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Override to handle address ForeignKey."""
        from django.db import models

        # Build data dict from model instance
        data = {}
        for field in obj._meta.fields:
            value = getattr(obj, field.name)
            # Handle ForeignKey fields
            if isinstance(field, models.ForeignKey):
                if value:
                    # Store the related object as a nested schema
                    if field.name == "address":
                        data["address"] = AddressSchema.model_validate(value)
                    else:
                        data[f"{field.name}_id"] = value.id
                else:
                    if field.name == "address":
                        data["address"] = None
                    else:
                        data[f"{field.name}_id"] = None
            else:
                data[field.name] = value

        # Handle rooms_list property
        if hasattr(obj, "rooms_list"):
            data["rooms_list"] = obj.rooms_list

        return super().model_validate(data, **kwargs)

    model_config = {"from_attributes": True}


class AdminRoomSchema(BaseModel):
    """Room row for the PulseFit staff admin."""

    id: uuid.UUID
    name: str
    capacity: int
    is_active: bool = False
    studio_id: uuid.UUID
    studio_name: str | None = None

    model_config = {"from_attributes": True}


class AdminStudioSchema(BaseModel):
    """Studio row for the PulseFit staff admin."""

    id: uuid.UUID
    name: str
    is_active: bool = False
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    address: Optional[AddressSchema] = None
    rooms: list[AdminRoomSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AdminStudioWriteSchema(BaseModel):
    """Create or update payload for a studio from the staff admin."""

    name: str | None = None
    is_active: bool | None = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    address_id: uuid.UUID | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class AdminRoomWriteSchema(BaseModel):
    """Create or update payload for a room from the staff admin."""

    studio_id: uuid.UUID | None = None
    name: str | None = None
    capacity: int | None = None
    is_active: bool | None = None


class StudioSettingsSchema(BaseModel):
    """Studio-wide policy settings."""

    free_cancellation_hours: int = Field(ge=0, le=168)

    model_config = {"from_attributes": True}


class StudioSettingsWriteSchema(BaseModel):
    """Partial update for studio settings (superuser only)."""

    free_cancellation_hours: int = Field(ge=0, le=168)


class StudioBrandingSchema(BaseModel):
    """Branding tokens returned by the public and admin endpoints."""

    name: str
    tagline: str
    logo_svg: str
    primary_color: str
    secondary_color: str
    background_color: str
    text_color: str
    heading_font: str
    body_font: str

    model_config = {"from_attributes": True}


class StudioBrandingWriteSchema(BaseModel):
    """Partial update of the studio branding (superuser only)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    tagline: str | None = Field(default=None, max_length=140)
    logo_svg: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    background_color: str | None = None
    text_color: str | None = None
    heading_font: str | None = None
    body_font: str | None = None

    @field_validator("name", "tagline")
    @classmethod
    def _strip_text(cls, value):
        if value is None:
            return value
        value = value.strip()
        if "<" in value or ">" in value:
            raise ValueError("No se permiten los caracteres < ni >.")
        return value

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value):
        if value is not None and not value:
            raise ValueError("El nombre no puede estar vacío.")
        return value

    @field_validator("primary_color", "secondary_color", "background_color", "text_color")
    @classmethod
    def _color(cls, value, info):
        if value is None:
            return value
        try:
            return validate_hex_color(value, info.field_name)
        except BrandingError as exc:
            raise ValueError(str(exc)) from None

    @field_validator("heading_font", "body_font")
    @classmethod
    def _font(cls, value, info):
        if value is None:
            return value
        try:
            return validate_font(value, info.field_name)
        except BrandingError as exc:
            raise ValueError(str(exc)) from None

    @field_validator("logo_svg")
    @classmethod
    def _logo(cls, value):
        if value is None:
            return value
        try:
            return sanitize_svg(value)
        except BrandingError as exc:
            raise ValueError(str(exc)) from None
