"""Tests for studios models, focusing on Studio.rooms_list property and Address model."""

import pytest

from apps.studios.models import Address, Room, Studio


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


class TestAddressModel:
    @pytest.mark.django_db
    def test_address_str_returns_address_string(self, address):
        assert str(address) == address.address
        assert str(address) == "123 Test St"

    @pytest.mark.django_db
    def test_address_can_have_null_coordinates(self, address):
        assert address.latitude is None
        assert address.longitude is None

    @pytest.mark.django_db
    def test_address_can_have_coordinates(self):
        address = Address.objects.create(
            address="Test Address",
            latitude=-33.4489,
            longitude=-70.6693,
        )
        assert address.latitude == -33.4489
        assert address.longitude == -70.6693

    @pytest.mark.django_db
    def test_studio_address_relationship(self, studio, address):
        assert studio.address == address
        assert address.studios.first() == studio

    @pytest.mark.django_db
    def test_studio_can_have_null_address(self):
        studio = Studio.objects.create(name="Studio Without Address", is_active=True)
        assert studio.address is None
