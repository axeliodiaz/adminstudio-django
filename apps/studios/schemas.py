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
    address: Optional[str] = None  # Address string from related Address object
    address_id: Optional[uuid.UUID] = None
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
                    # Store the related object's address string and id
                    if field.name == "address":
                        data["address"] = value.address
                        data["address_id"] = value.id
                    else:
                        data[f"{field.name}_id"] = value.id
                else:
                    if field.name == "address":
                        data["address"] = None
                        data["address_id"] = None
                    else:
                        data[f"{field.name}_id"] = None
            else:
                data[field.name] = value

        # Handle rooms_list property
        if hasattr(obj, "rooms_list"):
            data["rooms_list"] = obj.rooms_list

        return super().model_validate(data, **kwargs)

    model_config = {"from_attributes": True}
