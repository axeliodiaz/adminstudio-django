"""API tests for staff admin studio and room endpoints."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.studios.models import Address, Room, Studio

User = get_user_model()


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="adminuser",
        email="admin@example.com",
        password="pass1234",
        is_staff=True,
    )


@pytest.fixture
def staff_client(api_client, staff_user):
    token = ExpiringToken.objects.create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestAdminStudioViews:
    def test_list_requires_staff(self, api_client):
        user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="pass1234",
        )
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("admin-studio-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_returns_studios_with_rooms(self, staff_client, studio, room, extra_room):
        response = staff_client.get(reverse("admin-studio-list"))
        assert response.status_code == status.HTTP_200_OK
        ids = {row["id"] for row in response.data}
        assert str(studio.id) in ids
        match = next(row for row in response.data if row["id"] == str(studio.id))
        assert len(match["rooms"]) == 2

    def test_create_and_update_studio(self, staff_client):
        create_response = staff_client.post(
            reverse("admin-studio-list"),
            data={
                "name": "Lo Barnechea",
                "is_active": True,
                "opening_time": "07:00:00",
                "closing_time": "22:00:00",
                "address": "Patio Andino 4770",
                "latitude": -33.35,
                "longitude": -70.51,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        studio_id = create_response.data["id"]
        assert create_response.data["name"] == "Lo Barnechea"
        assert create_response.data["address"]["address"] == "Patio Andino 4770"

        update_response = staff_client.patch(
            reverse("admin-studio-detail", kwargs={"studio_id": studio_id}),
            data={"name": "PulseFit Lo Barnechea", "is_active": False},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["name"] == "PulseFit Lo Barnechea"
        assert update_response.data["is_active"] is False

    def test_create_and_update_room(self, staff_client, studio):
        create_response = staff_client.post(
            reverse("admin-room-list"),
            data={
                "studio_id": str(studio.id),
                "name": "Sala 1",
                "capacity": 24,
                "is_active": True,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        room_id = create_response.data["id"]
        assert create_response.data["studio_id"] == str(studio.id)

        update_response = staff_client.patch(
            reverse("admin-room-detail", kwargs={"room_id": room_id}),
            data={"capacity": 28, "is_active": False},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["capacity"] == 28
        assert update_response.data["is_active"] is False
        assert Room.objects.get(id=room_id).capacity == 28

    def test_create_studio_requires_name(self, staff_client):
        response = staff_client.post(
            reverse("admin-studio-list"),
            data={"is_active": True},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Address.objects.count() == 0
        assert Studio.objects.count() == 0
