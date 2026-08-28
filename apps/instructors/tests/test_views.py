"""API tests for InstructorViewSet (create, list, retrieve, update, partial_update)."""

import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.instructors.models import Instructor


class TestInstructorViewSet:
    @pytest.mark.django_db
    def test_create_instructor_returns_201_then_200_on_duplicate(
        self, api_client, registration_payload
    ):
        # First create -> 201
        resp1 = api_client.post(
            reverse("instructor-list"), data=registration_payload, format="json"
        )
        assert resp1.status_code == status.HTTP_201_CREATED
        data1 = resp1.json()
        assert set(data1.keys()) == {"first_name", "last_name"}
        assert Instructor.objects.count() == 1

        # Second call with same email -> 200 and does not create duplicates
        resp2 = api_client.post(
            reverse("instructor-list"), data=registration_payload, format="json"
        )
        assert resp2.status_code == status.HTTP_200_OK
        assert Instructor.objects.count() == 1

    @pytest.mark.django_db
    def test_list_instructors(self, api_client, instructor, another_instructor):
        resp = api_client.get(reverse("instructor-list"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        ids = {str(item.get("id")) for item in data}
        assert str(instructor.id) in ids
        assert str(another_instructor.id) in ids
        # Basic shape: id present; either user or user_id present depending on schema
        sample = data[0]
        assert "id" in sample
        assert ("user" in sample) or ("user_id" in sample)

    @pytest.mark.django_db
    def test_retrieve_instructor(self, api_client, instructor):
        resp = api_client.get(reverse("instructor-detail", args=[instructor.id]))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == str(instructor.id)
        assert ("user" in data) or ("user_id" in data)

    @pytest.mark.django_db
    def test_retrieve_instructor_404(self, api_client):
        resp = api_client.get(reverse("instructor-detail", args=[uuid.uuid4()]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["detail"] == "Not found."

    @pytest.mark.django_db
    def test_update_instructor_put_and_patch(self, api_client, instructor):
        # PUT update all fields
        put_payload = {
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "birthdate": "1990-12-31",
            "address": "New Address",
        }
        resp_put = api_client.put(
            reverse("instructor-detail", args=[instructor.id]), data=put_payload, format="json"
        )
        assert resp_put.status_code == status.HTTP_200_OK
        # Verify DB updated
        instructor.user.refresh_from_db()
        assert instructor.user.first_name == put_payload["first_name"]
        assert instructor.user.last_name == put_payload["last_name"]

        # PATCH update subset (sensitive fields like phone_number must be ignored)
        patch_payload = {"first_name": "Patched"}
        resp_patch = api_client.patch(
            reverse("instructor-detail", args=[instructor.id]), data=patch_payload, format="json"
        )
        assert resp_patch.status_code == status.HTTP_200_OK
        instructor.user.refresh_from_db()
        assert instructor.user.first_name == "Patched"

    @pytest.mark.django_db
    def test_update_instructor_put_404(self, api_client):
        put_payload = {
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "birthdate": "1990-12-31",
            "address": "New Address",
        }
        resp = api_client.put(
            reverse("instructor-detail", args=[uuid.uuid4()]), data=put_payload, format="json"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["detail"] == "Not found."

    @pytest.mark.django_db
    def test_update_instructor_patch_404(self, api_client):
        resp = api_client.patch(
            reverse("instructor-detail", args=[uuid.uuid4()]),
            data={"first_name": "Patched"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["detail"] == "Not found."
