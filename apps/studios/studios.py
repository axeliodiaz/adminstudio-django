from django.shortcuts import get_object_or_404

from apps.studios.models import Room, Studio


def get_studio_from_id(id) -> Studio:
    """Return a Studio by id or 404."""
    return get_object_or_404(Studio, pk=id)


def get_room_from_id(id) -> Room:
    """Return a StudioRoom by id or 404."""
    return get_object_or_404(Room, pk=id)


def studios_queryset():
    """Return a queryset of all studios with prefetched rooms."""
    return Studio.objects.all().prefetch_related("rooms")


def rooms_queryset():
    """Return a queryset of all rooms."""
    return Room.objects.all()
