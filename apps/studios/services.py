"""Services for studios app.

Encapsulate creation and update logic for Studio and StudioRoom models.
Also provide retrieval helpers to avoid model calls in views.
"""

from uuid import UUID

from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.studios.models import Address, Room, Studio, StudioSettings
from apps.studios.schemas import (
    AddressSchema,
    AdminRoomSchema,
    AdminStudioSchema,
    RoomSchema,
    StudioSchema,
    StudioSettingsSchema,
)
from apps.studios.studios import (
    addresses_queryset,
    get_address_from_id,
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


def get_address(pk) -> AddressSchema:
    """Return an AddressSchema by pk or 404."""
    return AddressSchema.model_validate(get_address_from_id(pk))


def get_list_addresses() -> list[AddressSchema]:
    """Return a list of AddressSchema for all addresses."""
    return [AddressSchema.model_validate(obj) for obj in addresses_queryset()]


def _serialize_admin_room(room: Room) -> dict:
    payload = {
        "id": room.id,
        "name": room.name,
        "capacity": room.capacity,
        "is_active": room.is_active,
        "studio_id": room.studio_id,
        "studio_name": room.studio.name if room.studio_id else None,
    }
    return AdminRoomSchema.model_validate(payload).model_dump(mode="json")


def _serialize_admin_studio(studio: Studio) -> dict:
    rooms = list(studio.rooms.all().order_by("name"))
    payload = {
        "id": studio.id,
        "name": studio.name,
        "is_active": studio.is_active,
        "opening_time": studio.opening_time,
        "closing_time": studio.closing_time,
        "address": AddressSchema.model_validate(studio.address) if studio.address else None,
        "rooms": [_serialize_admin_room(room) for room in rooms],
    }
    return AdminStudioSchema.model_validate(payload).model_dump(mode="json")


def list_admin_studios(*, search: str | None = None, status: str | None = None) -> list[dict]:
    """Return studios for the staff admin list."""
    queryset = Studio.objects.select_related("address").prefetch_related("rooms").order_by("name")

    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(name__icontains=term)
            | Q(address__address__icontains=term)
            | Q(rooms__name__icontains=term)
        ).distinct()

    return [_serialize_admin_studio(studio) for studio in queryset]


def get_admin_studio(*, studio_id: str | UUID) -> dict:
    studio = get_object_or_404(
        Studio.objects.select_related("address").prefetch_related("rooms"),
        id=studio_id,
    )
    return _serialize_admin_studio(studio)


def list_admin_rooms(
    *, studio_id: str | UUID | None = None, search: str | None = None
) -> list[dict]:
    queryset = Room.objects.select_related("studio").order_by("studio__name", "name")
    if studio_id:
        queryset = queryset.filter(studio_id=studio_id)
    term = (search or "").strip()
    if term:
        queryset = queryset.filter(Q(name__icontains=term) | Q(studio__name__icontains=term))
    return [_serialize_admin_room(room) for room in queryset]


def get_admin_room(*, room_id: str | UUID) -> dict:
    room = get_object_or_404(Room.objects.select_related("studio"), id=room_id)
    return _serialize_admin_room(room)


def _resolve_studio_address(*, data: dict, current: Address | None = None) -> Address | None:
    if "address_id" in data:
        address_id = data.get("address_id")
        if address_id is None:
            return None
        return get_object_or_404(Address, id=address_id)

    if "address" not in data and "latitude" not in data and "longitude" not in data:
        return current

    line = data.get("address")
    if line is not None:
        line = str(line).strip()
        if not line:
            return None

    if current is None:
        if not line:
            return None
        return Address.objects.create(
            address=line,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
        )

    dirty: list[str] = []
    if line is not None:
        current.address = line
        dirty.append("address")
    if "latitude" in data:
        current.latitude = data.get("latitude")
        dirty.append("latitude")
    if "longitude" in data:
        current.longitude = data.get("longitude")
        dirty.append("longitude")
    if dirty:
        current.save(update_fields=list(dict.fromkeys(dirty)))
    return current


def create_admin_studio(*, data: dict) -> dict:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("El nombre del estudio es obligatorio.")

    address = _resolve_studio_address(data=data, current=None)
    studio = Studio.objects.create(
        name=name,
        is_active=bool(data.get("is_active", False)),
        opening_time=data.get("opening_time"),
        closing_time=data.get("closing_time"),
        address=address,
    )
    return _serialize_admin_studio(studio)


def update_admin_studio(*, studio_id: str | UUID, data: dict) -> dict:
    studio = get_object_or_404(
        Studio.objects.select_related("address").prefetch_related("rooms"),
        id=studio_id,
    )

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("El nombre del estudio es obligatorio.")
        studio.name = name

    if "is_active" in data:
        studio.is_active = bool(data.get("is_active"))
    if "opening_time" in data:
        studio.opening_time = data.get("opening_time")
    if "closing_time" in data:
        studio.closing_time = data.get("closing_time")

    if any(key in data for key in ("address_id", "address", "latitude", "longitude")):
        studio.address = _resolve_studio_address(data=data, current=studio.address)

    studio.save()
    studio.refresh_from_db()
    return _serialize_admin_studio(studio)


def create_admin_room(*, data: dict) -> dict:
    studio_id = data.get("studio_id")
    if not studio_id:
        raise ValueError("El estudio es obligatorio.")
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("El nombre de la sala es obligatorio.")
    capacity = data.get("capacity")
    if capacity is None or int(capacity) < 0:
        raise ValueError("La capacidad debe ser un número mayor o igual a 0.")

    studio = get_object_or_404(Studio, id=studio_id)
    room = Room.objects.create(
        studio=studio,
        name=name,
        capacity=int(capacity),
        is_active=bool(data.get("is_active", False)),
    )
    return _serialize_admin_room(room)


def update_admin_room(*, room_id: str | UUID, data: dict) -> dict:
    room = get_object_or_404(Room.objects.select_related("studio"), id=room_id)

    if "studio_id" in data and data.get("studio_id"):
        room.studio = get_object_or_404(Studio, id=data["studio_id"])
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("El nombre de la sala es obligatorio.")
        room.name = name
    if "capacity" in data:
        capacity = data.get("capacity")
        if capacity is None or int(capacity) < 0:
            raise ValueError("La capacidad debe ser un número mayor o igual a 0.")
        room.capacity = int(capacity)
    if "is_active" in data:
        room.is_active = bool(data.get("is_active"))

    room.save()
    return _serialize_admin_room(room)


def get_studio_settings() -> dict:
    """Return current studio policy settings."""
    return StudioSettingsSchema.model_validate(StudioSettings.load()).model_dump()


def update_studio_settings(data: dict) -> dict:
    """Update studio policy settings (superuser callers only)."""
    settings_obj = StudioSettings.load()
    if "free_cancellation_hours" in data:
        hours = data["free_cancellation_hours"]
        if hours is None or int(hours) < 0:
            raise ValueError("free_cancellation_hours must be a non-negative integer.")
        settings_obj.free_cancellation_hours = int(hours)
        settings_obj.save(update_fields=["free_cancellation_hours", "modified"])
    return get_studio_settings()
