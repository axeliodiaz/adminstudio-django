import pytest
import uuid
from datetime import datetime, timedelta, timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.members.models import Member, Reservation
from apps.schedules import constants
from apps.schedules.models import Schedule


class TestScheduleViewSetList:
    @pytest.mark.django_db
    def test_list_no_filters(self, api_client, schedules_sample):
        resp = api_client.get(reverse("schedule-list"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3

    @pytest.mark.django_db
    def test_list_filter_by_start_time_valid(self, api_client, schedules_sample):
        threshold = (
            (schedules_sample[0].start_time + timedelta(minutes=30))
            .isoformat()
            .replace("+00:00", "Z")
        )
        resp = api_client.get(reverse("schedule-list"), {"start_time": threshold})
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.json()}
        assert ids == {str(schedules_sample[1].id), str(schedules_sample[2].id)}

    @pytest.mark.django_db
    def test_list_filter_by_start_time_invalid_format(self, api_client, schedules_sample):
        resp = api_client.get(reverse("schedule-list"), {"start_time": "not-a-datetime"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        body = resp.json()
        assert "Invalid start_time format" in body.get("detail", "")

    @pytest.mark.django_db
    def test_list_filter_by_instructor_id(self, api_client, schedules_sample):
        instructor_id = str(schedules_sample[0].instructor_id)
        resp = api_client.get(reverse("schedule-list"), {"instructor_id": instructor_id})
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.json()}
        assert ids == {str(schedules_sample[0].id), str(schedules_sample[1].id)}

    @pytest.mark.django_db
    def test_list_filter_by_room_name(self, api_client, schedules_sample):
        resp = api_client.get(reverse("schedule-list"), {"room_name": "main"})
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.json()}
        assert ids == {str(schedules_sample[0].id), str(schedules_sample[2].id)}

    @pytest.mark.django_db
    def test_list_combined_filters(self, api_client, schedules_sample):
        threshold = (
            (schedules_sample[0].start_time + timedelta(minutes=30))
            .isoformat()
            .replace("+00:00", "Z")
        )
        params = {
            "start_time": threshold,
            "instructor_id": str(schedules_sample[0].instructor_id),
            "room_name": "small",
        }
        resp = api_client.get(reverse("schedule-list"), params)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert [item["id"] for item in data] == [str(schedules_sample[1].id)]


class TestScheduleViewSetRetrieve:
    @pytest.mark.django_db
    def test_retrieve_success(self, api_client, schedules_sample):
        obj = schedules_sample[0]
        resp = api_client.get(reverse("schedule-detail", args=[obj.id]))
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
    def test_retrieve_not_found_returns_404(self, api_client):
        resp = api_client.get(reverse("schedule-detail", args=[uuid.uuid4()]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        data = resp.json()
        assert "detail" in data
        assert "Not found" in data["detail"]


class TestScheduleViewSetCreate:
    @pytest.mark.django_db
    def test_create_success_returns_201_and_persists(self, api_client, instructor_alice, room_main):
        payload = {
            "instructor_id": str(instructor_alice.id),
            "start_time": datetime(2025, 1, 3, 8, 30, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 55,
            "room_id": str(room_main.id),
            "status": constants.SCHEDULE_STATUS_SCHEDULED,
        }
        resp = api_client.post(reverse("schedule-list"), data=payload, format="json")
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
    def test_create_invalid_status_returns_400(self, api_client, instructor_alice, room_main):
        payload = {
            "instructor_id": str(instructor_alice.id),
            "start_time": datetime(2025, 1, 3, 9, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 45,
            "room_id": str(room_main.id),
            "status": "invalid-status",
        }
        resp = api_client.post(reverse("schedule-list"), data=payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_non_positive_duration_returns_400(
        self, api_client, instructor_alice, room_main
    ):
        payload = {
            "instructor_id": str(instructor_alice.id),
            "start_time": datetime(2025, 1, 3, 10, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 0,
            "room_id": str(room_main.id),
            "status": constants.SCHEDULE_STATUS_DRAFT,
        }
        resp = api_client.post(reverse("schedule-list"), data=payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_nonexistent_instructor_returns_400(self, api_client, room_main):
        payload = {
            "instructor_id": str(uuid.uuid4()),
            "start_time": datetime(2025, 1, 3, 11, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 45,
            "room_id": str(room_main.id),
            "status": constants.SCHEDULE_STATUS_DRAFT,
        }
        resp = api_client.post(reverse("schedule-list"), data=payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_nonexistent_room_returns_404(self, api_client, instructor_alice):
        payload = {
            "instructor_id": str(instructor_alice.id),
            "start_time": datetime(2025, 1, 3, 12, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "duration_minutes": 45,
            "room_id": str(uuid.uuid4()),
            "status": constants.SCHEDULE_STATUS_DRAFT,
        }
        resp = api_client.post(reverse("schedule-list"), data=payload, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestScheduleViewSetReservations:
    @pytest.mark.django_db
    def test_reservations_list_success(self, api_client, schedules_sample):
        """Test listing reservations for a specific schedule."""
        from model_bakery import baker

        schedule = schedules_sample[0]
        # Create a member and reservations for this schedule
        member = baker.make("members.Member")
        reservation1 = Reservation.objects.create(member=member, schedule=schedule, spot=1)
        reservation2 = Reservation.objects.create(member=member, schedule=schedule, spot=2)

        # Create a reservation for a different schedule (should not appear)
        other_schedule = schedules_sample[1]
        Reservation.objects.create(member=member, schedule=other_schedule, spot=1)

        # Call the reservations endpoint
        url = reverse("schedule-reservations", args=[schedule.id])
        resp = api_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify the reservations belong to the correct schedule
        reservation_ids = {item["id"] for item in data}
        assert reservation_ids == {str(reservation1.id), str(reservation2.id)}
        for item in data:
            assert item["schedule_id"] == str(schedule.id)
            assert "member_id" in item
            assert "status" in item
            assert "spot" in item

    @pytest.mark.django_db
    def test_reservations_list_empty(self, api_client, schedules_sample):
        """Test listing reservations for a schedule with no reservations."""
        schedule = schedules_sample[0]

        url = reverse("schedule-reservations", args=[schedule.id])
        resp = api_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.django_db
    def test_reservations_list_not_found(self, api_client):
        """Test listing reservations for a non-existent schedule."""
        url = reverse("schedule-reservations", args=[uuid.uuid4()])
        resp = api_client.get(url)

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        data = resp.json()
        assert "detail" in data
        assert "Not found" in data["detail"]
