"""Tests for apps.studios.studios helpers."""

import uuid

import pytest
from django.http import Http404

from apps.studios.models import Room, Studio
from apps.studios.studios import (
    get_room_from_id,
    get_studio_from_id,
    rooms_queryset,
    studios_queryset,
)


class TestGetStudioById:
    @pytest.mark.django_db
    def test_get_studio_from_id_returns_studio(self, studio):
        # Act
        result = get_studio_from_id(studio.id)
        # Assert
        assert isinstance(result, Studio)
        assert result.id == studio.id

    @pytest.mark.django_db
    def test_get_studio_from_id_raises_404(self):
        with pytest.raises(Http404):
            get_studio_from_id(uuid.uuid4())


class TestGetRoomById:
    @pytest.mark.django_db
    def test_get_room_from_id_returns_room(self, room):
        # Act
        result = get_room_from_id(room.id)
        # Assert
        assert isinstance(result, Room)
        assert result.id == room.id

    @pytest.mark.django_db
    def test_get_room_from_id_raises_404(self):
        with pytest.raises(Http404):
            get_room_from_id(uuid.uuid4())


class TestStudioQuerysets:
    @pytest.mark.django_db
    def test_studios_queryset_prefetches_rooms(self, django_assert_num_queries, room):
        # We created 1 studio with 1 room via fixtures.
        # Prefetch should execute 2 queries (studios + rooms) when evaluated,
        # and then accessing related rooms should not hit the DB again.
        with django_assert_num_queries(2):
            studios = list(studios_queryset())
        assert len(studios) == 1
        studio = studios[0]
        assert isinstance(studio, Studio)
        with django_assert_num_queries(0):
            rooms = list(studio.rooms.all())
        assert len(rooms) == 1
        assert rooms[0].id == room.id


class TestRoomQuerysets:
    @pytest.mark.django_db
    def test_rooms_queryset_returns_all_rooms(self, room, extra_room):
        # Arrange: use fixture to create an extra room
        extra = extra_room
        # Act
        qs = rooms_queryset()
        # Assert
        ids = set(str(r.id) for r in qs)
        assert str(room.id) in ids
        assert str(extra.id) in ids
        assert qs.count() == 2
