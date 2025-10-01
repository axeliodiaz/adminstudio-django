"""Tests for studios models, focusing on Studio.rooms_list property."""

import pytest

from apps.studios.models import Room, Studio


class TestStudioRoomsList:
    @pytest.mark.django_db
    def test_rooms_list_returns_concrete_list(self, studio, room, extra_room):
        # Act
        result = studio.rooms_list
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, Room) for r in result)
        ids = {str(r.id) for r in result}
        assert str(room.id) in ids
        assert str(extra_room.id) in ids

    @pytest.mark.django_db
    def test_rooms_list_uses_prefetch_cache(
        self, django_assert_num_queries, studio, room, extra_room
    ):
        # Evaluate queryset with prefetch
        with django_assert_num_queries(2):
            s = Studio.objects.filter(id=studio.id).prefetch_related("rooms").get()
        # Accessing rooms_list should not hit the DB again thanks to prefetch cache
        with django_assert_num_queries(0):
            result = s.rooms_list
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.django_db
    def test_rooms_list_empty_for_studio_without_rooms(self, empty_studio):
        assert empty_studio.rooms.count() == 0
        assert empty_studio.rooms_list == []
