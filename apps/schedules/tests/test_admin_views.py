"""API tests for staff admin schedule endpoints."""

from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.members import constants as member_constants
from apps.members.models import Member, Reservation
from apps.schedules import constants
from apps.schedules.models import Schedule

User = get_user_model()


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="scheduleadmin",
        email="scheduleadmin@example.com",
        password="pass1234",
        is_staff=True,
    )


@pytest.fixture
def staff_client(api_client, staff_user):
    token = ExpiringToken.objects.create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestAdminScheduleViews:
    def test_list_requires_staff(self, api_client, schedules_sample):
        user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="pass1234",
        )
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("admin-schedule-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_returns_nested_labels(self, staff_client, schedules_sample):
        response = staff_client.get(reverse("admin-schedule-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3
        row = response.data[0]
        assert row["instructor_name"]
        assert row["room_name"]
        assert "reservation_count" in row

    def test_list_filters_by_range_and_status(self, staff_client, schedules_sample):
        sample = schedules_sample[0]
        sample.status = constants.SCHEDULE_STATUS_DRAFT
        sample.save(update_fields=["status"])

        start = sample.start_time.isoformat().replace("+00:00", "Z")
        end = (sample.start_time + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        response = staff_client.get(
            reverse("admin-schedule-list"),
            {
                "start_time": start,
                "end_time": end,
                "status": constants.SCHEDULE_STATUS_DRAFT,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert [row["id"] for row in response.data] == [str(sample.id)]

    def test_create_repeat_weeks_and_update_and_delete(
        self, staff_client, instructor_alice, room_main
    ):
        create_response = staff_client.post(
            reverse("admin-schedule-list"),
            data={
                "title": "RIDE 45",
                "description": "Full body",
                "instructor_id": str(instructor_alice.id),
                "room_id": str(room_main.id),
                "start_time": datetime(2026, 8, 24, 7, 0, tzinfo=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "duration_minutes": 45,
                "status": constants.SCHEDULE_STATUS_SCHEDULED,
                "repeat_weeks": 3,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        assert create_response.data["title"] == "RIDE 45"
        assert create_response.data["copies_created"] == 3
        assert Schedule.objects.filter(title="RIDE 45").count() == 3

        schedule_id = create_response.data["id"]
        update_response = staff_client.patch(
            reverse("admin-schedule-detail", kwargs={"schedule_id": schedule_id}),
            data={"title": "RIDE 60", "duration_minutes": 60},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["title"] == "RIDE 60"
        assert update_response.data["duration_minutes"] == 60

        delete_response = staff_client.delete(
            reverse("admin-schedule-detail", kwargs={"schedule_id": schedule_id})
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        assert Schedule.objects.filter(id=schedule_id).count() == 0

    def test_delete_blocked_when_reservations_exist(self, staff_client, schedules_sample):
        schedule = schedules_sample[0]
        member_user = User.objects.create_user(
            username="rider",
            email="rider@example.com",
            password="pass1234",
        )
        member = Member.objects.create(user=member_user)
        Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=member_constants.RESERVATION_STATUS_RESERVED,
        )

        response = staff_client.delete(
            reverse("admin-schedule-detail", kwargs={"schedule_id": schedule.id})
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "reservas activas" in response.data["detail"]
        assert Schedule.objects.filter(id=schedule.id).exists()
