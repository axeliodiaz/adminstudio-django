"""API tests for plans viewset using services-backed Pydantic schemas."""

import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.plans.models import Plan


class TestPlanViewSet:
    @pytest.mark.django_db
    def test_list_plans_returns_only_active(self, api_client):
        # Arrange: create active and inactive plans
        p_active_1 = Plan.objects.create(name="A1", type="MEMBERSHIP", price=10.0, is_active=True)
        p_active_2 = Plan.objects.create(name="A2", type="PACKAGE", price=20.0, is_active=True)
        p_inactive = Plan.objects.create(name="I1", type="MEMBERSHIP", price=5.0, is_active=False)

        resp = api_client.get(reverse("plan-list"))

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        ids = {item["id"] for item in data}
        assert str(p_active_1.id) in ids
        assert str(p_active_2.id) in ids
        assert str(p_inactive.id) not in ids

        # Basic field checks (schema serializes via Pydantic)
        sample = data[0]
        assert {
            "id",
            "name",
            "type",
            "price",
            "is_active",
            "is_popular",
            "is_highlighted",
            "created",
            "modified",
        }.issubset(sample.keys())

    @pytest.mark.django_db
    def test_retrieve_plan(self, api_client, plan):
        resp = api_client.get(reverse("plan-detail", args=[plan.id]))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == str(plan.id)
        assert data["name"] == plan.name

    @pytest.mark.django_db
    def test_retrieve_plan_404(self, api_client):
        resp = api_client.get(reverse("plan-detail", args=[uuid.uuid4()]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
