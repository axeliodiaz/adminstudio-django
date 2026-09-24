"""Default pagination on schedules lists (CYC-80 phase 3)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from drf_expiring_token.models import ExpiringToken

from apps.instructors.models import Instructor
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule
from apps.studios.models import Address, Room, Studio

User = get_user_model()


@pytest.fixture
def staff_client(api_client):
    staff = User.objects.create_user(
        username="staffer", email="staff@example.com", password="x", is_staff=True
    )
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def schedules(db):
    address = Address.objects.create(address="Addr")
    studio = Studio.objects.create(name="S1", address=address, is_active=True)
    room = Room.objects.create(studio=studio, name="R1", capacity=10, is_active=True)
    instructor_user = User.objects.create_user(
        username="coach", email="coach@example.com", password="x", first_name="Camila"
    )
    instructor = Instructor.objects.create(user=instructor_user)
    base = timezone.now() + timedelta(days=1)
    rows = []
    for i in range(7):
        rows.append(
            Schedule.objects.create(
                title=f"RIDE {i:02d}",
                instructor=instructor,
                room=room,
                status=schedule_constants.SCHEDULE_STATUS_SCHEDULED,
                start_time=base + timedelta(hours=i),
            )
        )
    return rows


@pytest.mark.django_db
class TestAdminSchedulesPagination:
    def test_without_page_params_returns_first_page(self, staff_client, schedules):
        resp = staff_client.get(reverse("admin-schedule-list"))
        assert resp.status_code == 200
        assert resp.data["count"] == 7
        assert len(resp.data["results"]) == 7

    def test_page_envelope(self, staff_client, schedules):
        resp = staff_client.get(reverse("admin-schedule-list"), {"page": 2, "page_size": 3})
        assert resp.status_code == 200
        body = resp.data
        assert body["count"] == 7
        assert body["page"] == 2
        assert body["total_pages"] == 3
        assert body["next_page"] == 3
        assert body["previous_page"] == 1
        assert len(body["results"]) == 3

    def test_invalid_page_returns_400(self, staff_client, schedules):
        resp = staff_client.get(reverse("admin-schedule-list"), {"page": "0"})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestPublicSchedulesPagination:
    def test_without_page_params_returns_first_page(self, api_client, schedules):
        resp = api_client.get(reverse("schedule-list"))
        assert resp.status_code == 200
        assert resp.data["count"] == 7
        assert len(resp.data["results"]) == 7

    def test_page_envelope_keeps_row_shape(self, api_client, schedules):
        resp = api_client.get(reverse("schedule-list"), {"page": 1, "page_size": 5})
        assert resp.status_code == 200
        body = resp.data
        assert body["count"] == 7
        assert body["total_pages"] == 2
        assert len(body["results"]) == 5
        row = body["results"][0]
        assert "booked_count" in row
        assert "capacity" in row
        assert "instructor_name" in row

    def test_page_two(self, api_client, schedules):
        resp = api_client.get(reverse("schedule-list"), {"page": 2, "page_size": 5})
        assert resp.status_code == 200
        assert len(resp.data["results"]) == 2
