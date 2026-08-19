"""API tests for staff admin plan endpoints."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.plans import constants
from apps.plans.models import Benefit, Plan

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
class TestAdminPlanViews:
    def test_list_requires_staff(self, api_client):
        user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="pass1234",
        )
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("admin-plan-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_returns_active_and_inactive(self, staff_client):
        active = Plan.objects.create(
            name="Active Plan",
            type=constants.PLAN_TYPE_MEMBERSHIP,
            price=10.0,
            is_active=True,
        )
        inactive = Plan.objects.create(
            name="Inactive Plan",
            type=constants.PLAN_TYPE_PACKAGE,
            price=20.0,
            is_active=False,
        )

        response = staff_client.get(reverse("admin-plan-list"))
        assert response.status_code == status.HTTP_200_OK
        ids = {row["id"] for row in response.data}
        assert str(active.id) in ids
        assert str(inactive.id) in ids

    def test_list_filters_by_type_and_status(self, staff_client):
        Plan.objects.create(
            name="Membership Active",
            type=constants.PLAN_TYPE_MEMBERSHIP,
            price=10.0,
            is_active=True,
        )
        Plan.objects.create(
            name="Package Inactive",
            type=constants.PLAN_TYPE_PACKAGE,
            price=20.0,
            is_active=False,
        )

        response = staff_client.get(
            reverse("admin-plan-list"),
            {"type": constants.PLAN_TYPE_MEMBERSHIP, "status": "active"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Membership Active"

    def test_create_and_update_plan(self, staff_client):
        benefit = Benefit.objects.create(
            name="Priority booking",
            description="Book early",
            is_active=True,
        )

        create_response = staff_client.post(
            reverse("admin-plan-list"),
            data={
                "name": "Gold",
                "type": constants.PLAN_TYPE_MEMBERSHIP,
                "price": 49.99,
                "duration_days": 30,
                "classes_included": None,
                "guest_passes_included": 2,
                "is_active": True,
                "is_popular": True,
                "is_highlighted": False,
                "benefit_ids": [str(benefit.id)],
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        plan_id = create_response.data["id"]
        assert create_response.data["name"] == "Gold"
        assert create_response.data["guest_passes_included"] == 2
        assert create_response.data["benefit_ids"] == [str(benefit.id)]

        update_response = staff_client.patch(
            reverse("admin-plan-detail", kwargs={"plan_id": plan_id}),
            data={
                "name": "Gold Plus",
                "is_highlighted": True,
                "benefit_ids": [],
            },
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["name"] == "Gold Plus"
        assert update_response.data["is_highlighted"] is True
        assert update_response.data["benefit_ids"] == []

    def test_detail_requires_staff(self, api_client):
        plan = Plan.objects.create(
            name="Solo",
            type=constants.PLAN_TYPE_MEMBERSHIP,
            price=10.0,
            is_active=True,
        )
        response = api_client.get(reverse("admin-plan-detail", kwargs={"plan_id": plan.id}))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_benefits_list(self, staff_client):
        Benefit.objects.create(name="Freeze", description="Pause", is_active=True)
        Benefit.objects.create(name="Hidden", description="Off", is_active=False)

        response = staff_client.get(reverse("admin-benefit-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

        active_only = staff_client.get(reverse("admin-benefit-list"), {"status": "active"})
        assert active_only.status_code == status.HTTP_200_OK
        assert len(active_only.data) == 1
        assert active_only.data[0]["name"] == "Freeze"
