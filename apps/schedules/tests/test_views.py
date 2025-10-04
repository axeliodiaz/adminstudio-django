import pytest
import uuid
from datetime import datetime, timedelta, timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.schedules import constants
from apps.schedules.models import Schedule


class TestScheduleViewSetList:
    @pytest.mark.django_db
    def test_list_no_filters(self, schedules_sample):
        client = APIClient()
        resp = client.get(reverse("schedule-list"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3

    @pytest.mark.django_db
    def test_list_filter_by_start_time_valid(self, schedules_sample):
        client = APIClient()
        threshold = (
            (schedules_sample[0].start_time + timedelta(minutes=30))
            .isoformat()
            .replace("+00:00", "Z")
        )
        resp = client.get(reverse("schedule-list"), {"start_time": threshold})
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.json()}
        assert ids == {str(schedules_sample[1].id), str(schedules_sample[2].id)}

    @pytest.mark.django_db
    def test_list_filter_by_start_time_invalid_format(self, schedules_sample):
        client = APIClient()
        resp = client.get(reverse("schedule-list"), {"start_time": "not-a-datetime"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        body = resp.json()
        assert "Invalid start_time format" in body.get("detail", "")

    @pytest.mark.django_db
    def test_list_filter_by_instructor_username(self, schedules_sample):
        client = APIClient()
        resp = client.get(reverse("schedule-list"), {"instructor": "ali"})
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.json()}
        assert ids == {str(schedules_sample[0].id), str(schedules_sample[1].id)}

    @pytest.mark.django_db
    def test_list_filter_by_room_name(self, schedules_sample):
        client = APIClient()
        resp = client.get(reverse("schedule-list"), {"room_name": "main"})
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.json()}
        assert ids == {str(schedules_sample[0].id), str(schedules_sample[2].id)}

    @pytest.mark.django_db
    def test_list_combined_filters(self, schedules_sample):
        client = APIClient()
        threshold = (
            (schedules_sample[0].start_time + timedelta(minutes=30))
            .isoformat()
            .replace("+00:00", "Z")
        )
        params = {"start_time": threshold, "instructor": "ali", "room_name": "small"}
        resp = client.get(reverse("schedule-list"), params)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert [item["id"] for item in data] == [str(schedules_sample[1].id)]


class TestScheduleViewSetRetrieve:
    @pytest.mark.django_db
    def test_retrieve_success(self, schedules_sample):
        client = APIClient()
        obj = schedules_sample[0]
        resp = client.get(reverse("schedule-detail", args=[obj.id]))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        # Basic shape and matching fields
        assert data["id"] == str(obj.id)
        assert data["instructor"] == str(obj.instructor_id)
        assert data["room"] == str(obj.room_id)
        assert data["duration_minutes"] == obj.duration_minutes
        assert data["status"] == obj.status
        assert "created" in data and "modified" in data

    @pytest.mark.django_db
    def test_retrieve_not_found_returns_500(self):
        client = APIClient()
        client.raise_request_exception = False
        resp = client.get(reverse("schedule-detail", args=[uuid.uuid4()]))
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestScheduleViewSetCreate:
    @pytest.mark.django_db
    def test_create_success_returns_201_and_persists(self, instructor_alice, room_main):
        client = APIClient()
        payload = {
            "instructor_id": str(instructor_alice.id),
            "start_time": datetime(2025, 1, 3, 8, 30, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 55,
            "room_id": str(room_main.id),
            "status": constants.SCHEDULE_STATUS_SCHEDULED,
        }
        resp = client.post(reverse("schedule-list"), data=payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert set(
            [
                "id",
                "created",
                "modified",
                "instructor_id",
                "start_time",
                "duration_minutes",
                "room_id",
                "status",
            ]
        ).issubset(data.keys())
        # Verify persisted in DB
        obj = Schedule.objects.get(id=data["id"])  # raises if not found
        assert str(obj.instructor_id) == payload["instructor_id"]
        assert str(obj.room_id) == payload["room_id"]
        assert obj.duration_minutes == payload["duration_minutes"]
        assert obj.status == payload["status"]

    @pytest.mark.django_db
    def test_create_invalid_status_returns_400(self, instructor_alice, room_main):
        client = APIClient()
        payload = {
            "instructor_id": str(instructor_alice.id),
            "start_time": datetime(2025, 1, 3, 9, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 45,
            "room_id": str(room_main.id),
            "status": "invalid-status",
        }
        resp = client.post(reverse("schedule-list"), data=payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_non_positive_duration_returns_400(self, instructor_alice, room_main):
        client = APIClient()
        payload = {
            "instructor_id": str(instructor_alice.id),
            "start_time": datetime(2025, 1, 3, 10, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 0,
            "room_id": str(room_main.id),
            "status": constants.SCHEDULE_STATUS_DRAFT,
        }
        resp = client.post(reverse("schedule-list"), data=payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_nonexistent_instructor_returns_400(self, room_main):
        client = APIClient()
        payload = {
            "instructor_id": str(uuid.uuid4()),
            "start_time": datetime(2025, 1, 3, 11, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 45,
            "room_id": str(room_main.id),
            "status": constants.SCHEDULE_STATUS_DRAFT,
        }
        resp = client.post(reverse("schedule-list"), data=payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_nonexistent_room_returns_404(self, instructor_alice):
        client = APIClient()
        payload = {
            "instructor_id": str(instructor_alice.id),
            "start_time": datetime(2025, 1, 3, 12, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 45,
            "room_id": str(uuid.uuid4()),
            "status": constants.SCHEDULE_STATUS_DRAFT,
        }
        resp = client.post(reverse("schedule-list"), data=payload, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
