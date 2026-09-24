"""Opt-in pagination on staff members/reservations lists (CYC-80)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from drf_expiring_token.models import ExpiringToken

from apps.instructors.models import Instructor
from apps.members.models import Member, Reservation
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
def members(db):
    rows = []
    for i in range(7):
        user = User.objects.create_user(
            username=f"m{i}@ex.com", email=f"m{i}@ex.com", password="x", first_name=f"Ana{i:02d}"
        )
        rows.append(Member.objects.create(user=user))
    return rows


@pytest.mark.django_db
class TestAdminMembersPagination:
    def test_without_page_params_returns_plain_list(self, staff_client, members):
        resp = staff_client.get(reverse("admin-members"))
        assert resp.status_code == 200
        assert isinstance(resp.data, list)
        assert len(resp.data) == 7

    def test_page_envelope(self, staff_client, members):
        resp = staff_client.get(reverse("admin-members"), {"page": 2, "page_size": 3})
        assert resp.status_code == 200
        body = resp.data
        assert body["count"] == 7
        assert body["page"] == 2
        assert body["page_size"] == 3
        assert body["total_pages"] == 3
        assert body["next_page"] == 3
        assert body["previous_page"] == 1
        assert [row["first_name"] for row in body["results"]] == ["Ana03", "Ana04", "Ana05"]

    def test_page_past_end_is_empty(self, staff_client, members):
        resp = staff_client.get(reverse("admin-members"), {"page": 9, "page_size": 5})
        assert resp.status_code == 200
        assert resp.data["results"] == []
        assert resp.data["next_page"] is None

    def test_page_size_is_capped(self, staff_client, members):
        resp = staff_client.get(reverse("admin-members"), {"page_size": 10_000})
        assert resp.data["page_size"] == 200

    def test_search_applies_before_paging(self, staff_client, members):
        resp = staff_client.get(reverse("admin-members"), {"page": 1, "search": "Ana06"})
        assert resp.data["count"] == 1

    @pytest.mark.parametrize("value", ["0", "-1", "abc"])
    def test_invalid_values_return_400(self, staff_client, members, value):
        resp = staff_client.get(reverse("admin-members"), {"page": value})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestAdminReservationsPagination:
    def test_page_envelope(self, staff_client, members):
        studio = Studio.objects.create(
            name="S", address=Address.objects.create(address="A"), is_active=True
        )
        room = Room.objects.create(studio=studio, name="R", capacity=20, is_active=True)
        coach = Instructor.objects.create(
            user=User.objects.create_user(username="coach", email="c@ex.com", password="x")
        )
        start = timezone.now() + timedelta(hours=1)
        schedule = Schedule.objects.create(
            instructor=coach, room=room, start_time=start, duration_minutes=45, status="scheduled"
        )
        for i, member in enumerate(members):
            Reservation.objects.create(member=member, schedule=schedule, spot=i + 1)

        url = reverse("admin-reservation-list")
        plain = staff_client.get(url, {"schedule_id": str(schedule.id)})
        assert isinstance(plain.data, list) and len(plain.data) == 7

        resp = staff_client.get(url, {"schedule_id": str(schedule.id), "page": 3, "page_size": 3})
        assert resp.status_code == 200
        assert resp.data["count"] == 7
        assert [row["spot"] for row in resp.data["results"]] == [7]
        assert resp.data["previous_page"] == 2
