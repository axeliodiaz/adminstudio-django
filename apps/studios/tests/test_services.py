"""Tests for apps.studios.services."""

import uuid

import pytest
from django.http import Http404

from apps.studios.models import Room, Studio
from apps.studios.schemas import RoomSchema, StudioSchema
from apps.studios.services import get_list_rooms, get_list_studios, get_room, get_studio


class TestGetStudio:
    @pytest.mark.django_db
    def test_get_studio_returns_schema(self, studio, room):
        # Act
        result = get_studio(studio.id)
        # Assert
        assert isinstance(result, StudioSchema)
        assert result.id == studio.id
        assert result.name == studio.name
        assert result.address == studio.address
        # Should include rooms via rooms_list alias
        assert isinstance(result.rooms, list)
        assert len(result.rooms) == 1
        assert isinstance(result.rooms[0], RoomSchema)
        assert result.rooms[0].id == room.id

    @pytest.mark.django_db
    def test_get_studio_raises_404(self):
        with pytest.raises(Http404):
            get_studio(uuid.uuid4())


class TestGetRoom:
    @pytest.mark.django_db
    def test_get_room_returns_schema(self, room):
        # Act
        result = get_room(room.id)
        # Assert
        assert isinstance(result, RoomSchema)
        assert result.id == room.id
        assert result.name == room.name
        assert result.capacity == room.capacity
        assert result.studio_id == room.studio.id

    @pytest.mark.django_db
    def test_get_room_raises_404(self):
        with pytest.raises(Http404):
            get_room(uuid.uuid4())


class TestListFunctions:
    @pytest.mark.django_db
    def test_get_list_studios_returns_schemas_and_includes_rooms(self, studio, room):
        # Arrange: create another studio without rooms
        Studio.objects.create(name="Empty Studio", address="Nowhere", is_active=False)
        # Act
        result = get_list_studios()
        # Assert
        assert isinstance(result, list)
        assert all(isinstance(item, StudioSchema) for item in result)
        # There should be 2 studios (one with a room, one without)
        assert len(result) == 2
        # Find our original studio
        by_id = {str(item.id): item for item in result}
        s1 = by_id[str(studio.id)]
        assert isinstance(s1.rooms, list)
        assert len(s1.rooms) == 1
        assert isinstance(s1.rooms[0], RoomSchema)
        assert s1.rooms[0].id == room.id
        # The empty studio should have an empty list of rooms (not None)
        empty = next(x for x in result if x.id != studio.id)
        assert empty.rooms == []

    @pytest.mark.django_db
    def test_get_list_rooms_returns_all_room_schemas(self, room, extra_room):
        # Act
        result = get_list_rooms()
        # Assert
        assert isinstance(result, list)
        assert all(isinstance(item, RoomSchema) for item in result)
        ids = {str(item.id) for item in result}
        assert str(room.id) in ids
        assert str(extra_room.id) in ids
        assert len(result) == 2
