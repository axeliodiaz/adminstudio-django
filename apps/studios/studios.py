from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from apps.studios.models import Address, Location, Room, Studio


def get_studio_from_id(id) -> Studio:
    """Return a Studio by id or 404."""
    return get_object_or_404(Studio, pk=id)


def get_room_from_id(id) -> Room:
    """Return a StudioRoom by id or 404."""
    return get_object_or_404(Room, pk=id)


def studios_queryset():
    """Return a queryset of all studios with prefetched sedes and rooms."""
    locations = (
        Location.objects.select_related("address").order_by("name").prefetch_related("rooms")
    )
    return Studio.objects.select_related("address").prefetch_related(
        Prefetch("locations", queryset=locations),
    )


def rooms_queryset():
    """Return a queryset of all rooms."""
    return Room.objects.all()


def get_address_from_id(id) -> Address:
    """Return an Address by id or 404."""
    return get_object_or_404(Address, pk=id)


def addresses_queryset():
    """Return a queryset of addresses linked to active studios."""
    return Address.objects.filter(studios__is_active=True).distinct()
