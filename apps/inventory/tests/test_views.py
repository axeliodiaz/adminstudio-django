"""Access and base CRUD tests for the Inventory module (CYC-414)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.inventory.models import Category, Item, Location

User = get_user_model()


@pytest.fixture
def member_client(api_client):
    member = User.objects.create_user(
        username="inv.member",
        email="inv.member@example.com",
        password="testpass123",
    )
    token = ExpiringToken.objects.create(user=member)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def plain_staff_client(api_client):
    staff = User.objects.create_user(
        username="plain.staff",
        email="plain.staff@example.com",
        password="testpass123",
        is_staff=True,
    )
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def staff_client(api_client):
    staff = User.objects.create_user(
        username="inv.admin",
        email="inv.admin@example.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
    )
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestInventoryModuleView:
    def test_anonymous_gets_401(self, api_client):
        response = api_client.get(reverse("inventory-module"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_staff_gets_403(self, member_client):
        response = member_client.get(reverse("inventory-module"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_gets_module_info(self, staff_client):
        response = staff_client.get(reverse("inventory-module"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["module"] == "inventory"
        assert response.data["features"]["items"] is True
        assert response.data["features"]["suppliers"] is False


@pytest.mark.django_db
class TestInventoryCrud:
    def test_non_staff_cannot_create(self, member_client):
        response = member_client.post(
            reverse("inventory-categories"), {"name": "Bikes"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_category_create_and_list(self, staff_client):
        response = staff_client.post(
            reverse("inventory-categories"), {"name": "Bikes"}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Bikes"
        listing = staff_client.get(reverse("inventory-categories"))
        assert [row["name"] for row in listing.data["results"]] == ["Bikes"]

    def test_category_name_required(self, staff_client):
        response = staff_client.post(reverse("inventory-categories"), {"name": " "}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_location_kind_validation(self, staff_client):
        response = staff_client.post(
            reverse("inventory-locations"),
            {"name": "Sala 1", "kind": "attic"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        ok = staff_client.post(
            reverse("inventory-locations"),
            {"name": "Sala 1", "kind": "room"},
            format="json",
        )
        assert ok.status_code == status.HTTP_201_CREATED
        assert ok.data["kind"] == "room"

    def test_item_assignment_to_location_spot(self, staff_client):
        category = Category.objects.create(name="Bikes")
        location = Location.objects.create(name="Sala 1", kind=Location.ROOM)
        response = staff_client.post(
            reverse("inventory-items"),
            {
                "name": "Bike 12",
                "category_id": str(category.id),
                "location_id": str(location.id),
                "spot": "Spot 12",
                "identifier": "BIKE-012",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["location_name"] == "Sala 1"
        assert response.data["spot"] == "Spot 12"
        listing = staff_client.get(reverse("inventory-items"), {"location": str(location.id)})
        assert [row["name"] for row in listing.data["results"]] == ["Bike 12"]

    def test_item_requires_valid_category(self, staff_client):
        import uuid

        response = staff_client.post(
            reverse("inventory-items"),
            {"name": "Bike 13", "category_id": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAdminOnlyAccess:
    def test_plain_staff_gets_403(self, plain_staff_client):
        response = plain_staff_client.get(reverse("inventory-module"))
        assert response.status_code == status.HTTP_403_FORBIDDEN
