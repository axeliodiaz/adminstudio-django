import uuid
from datetime import datetime, time
from typing import Optional

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
