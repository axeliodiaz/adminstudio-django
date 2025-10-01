"""Services for studios app.

Encapsulate creation and update logic for Studio and StudioRoom models.
Also provide retrieval helpers to avoid model calls in views.
"""

from apps.studios.schemas import RoomSchema, StudioSchema
from apps.studios.studios import (
    get_room_from_id,
    get_studio_from_id,
    rooms_queryset,
    studios_queryset,
)


def get_studio(pk) -> StudioSchema:
    """Return a StudioSchema by pk or 404."""
    return StudioSchema.model_validate(get_studio_from_id(pk))


def get_room(pk) -> RoomSchema:
    """Return a RoomSchema by pk or 404."""
    return RoomSchema.model_validate(get_room_from_id(pk))


def get_list_studios() -> list[StudioSchema]:
    """Return a list of StudioSchema for all studios."""
    return [StudioSchema.model_validate(obj) for obj in studios_queryset()]


def get_list_rooms() -> list[RoomSchema]:
    """Return a list of RoomSchema for all rooms."""
    return [RoomSchema.model_validate(obj) for obj in rooms_queryset()]
