"""API tests for studios and rooms viewsets."""

import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class TestStudioViewSet:
    @pytest.mark.django_db
    def test_list_studios(self, api_client, studio, empty_studio):
        resp = api_client.get(reverse("studio-list"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        # Should include both studios
        ids = {item["id"] for item in data}
        assert str(studio.id) in ids
        assert str(empty_studio.id) in ids
        # Serializer fields check (rooms are not included by StudioSerializer)
        sample = data[0]
        assert set(["id", "name", "address", "is_active", "created", "modified"]).issubset(
            sample.keys()
        )
        # Address should be an object (or null)
        assert sample["address"] is None or isinstance(sample["address"], dict)
        if sample["address"]:
            assert "id" in sample["address"]
            assert "address" in sample["address"]
        assert "rooms" not in sample

    @pytest.mark.django_db
    def test_retrieve_studio(self, api_client, studio):
        resp = api_client.get(reverse("studio-detail", args=[studio.id]))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == str(studio.id)
        assert data["name"] == studio.name
        # Address should be an object with full Address details
        assert "address" in data
        if data["address"]:
            assert isinstance(data["address"], dict)
            assert "id" in data["address"]
            assert "address" in data["address"]
            assert data["address"]["address"] == studio.address.address
        assert "rooms" not in data  # StudioSerializer does not expose rooms

    @pytest.mark.django_db
    def test_retrieve_studio_404(self, api_client):
        resp = api_client.get(reverse("studio-detail", args=[uuid.uuid4()]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestRoomViewSet:
    @pytest.mark.django_db
    def test_list_rooms(self, api_client, room, extra_room):
        resp = api_client.get(reverse("room-list"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        ids = {item["id"] for item in data}
        assert str(room.id) in ids
        assert str(extra_room.id) in ids
        sample = data[0]
        assert {"id", "studio", "name", "capacity", "is_active", "created", "modified"}.issubset(
            sample.keys()
        )

    @pytest.mark.django_db
    def test_retrieve_room(self, api_client, room):
        resp = api_client.get(reverse("room-detail", args=[room.id]))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == str(room.id)
        assert data["name"] == room.name
        assert data["studio"] == str(room.studio_id)

    @pytest.mark.django_db
    def test_retrieve_room_404(self, api_client):
        resp = api_client.get(reverse("room-detail", args=[uuid.uuid4()]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
