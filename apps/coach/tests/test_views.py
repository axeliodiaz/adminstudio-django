from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework.test import APIClient

from apps.coach.models import ClassRating
from apps.instructors.models import Instructor
from apps.members import constants as member_constants
from apps.members.models import Member, Reservation
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule
from apps.studios.models import Address, Studio, Room

User = get_user_model()
SANTIAGO = ZoneInfo("America/Santiago")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def member_user():
    return User.objects.create_user(
        username="coachmember",
        email="coachmember@example.com",
        password="pass1234",
        first_name="Mia",
        last_name="Rider",
    )


@pytest.fixture
def member(member_user):
    return Member.objects.create(user=member_user)


@pytest.fixture
def coach_user():
    return User.objects.create_user(
        username="coachuser",
        email="coach@example.com",
        password="pass1234",
        first_name="Tomás",
        last_name="Muñoz",
        phone_number="+56911111111",
    )


@pytest.fixture
def instructor(coach_user):
    return Instructor.objects.create(
        user=coach_user,
        tagline="Power Ride",
        description="Bio",
        instagram_username="tomasride",
        specialties=["Power Ride"],
        languages=["Español"],
        certifications=["Schwinn"],
    )


@pytest.fixture
def other_instructor():
    user = User.objects.create_user(username="othercoach", password="pass1234")
    return Instructor.objects.create(user=user)


@pytest.fixture
def room():
    address = Address.objects.create(address="Addr")
    studio = Studio.objects.create(name="PulseFit", address=address, is_active=True)
    return Room.objects.create(studio=studio, name="Sala A", capacity=40, is_active=True)


@pytest.fixture
def schedule(instructor, room):
    start = datetime(2026, 8, 22, 19, 0, tzinfo=SANTIAGO)
    return Schedule.objects.create(
        title="HIIT Ride",
        instructor=instructor,
        start_time=start,
        duration_minutes=45,
        room=room,
        status=schedule_constants.SCHEDULE_STATUS_SCHEDULED,
    )


@pytest.fixture
def past_schedule(instructor, room):
    start = datetime(2026, 8, 20, 7, 0, tzinfo=SANTIAGO)
    return Schedule.objects.create(
        title="Power Ride",
        instructor=instructor,
        start_time=start,
        duration_minutes=45,
        room=room,
        status=schedule_constants.SCHEDULE_STATUS_COMPLETED,
    )


@pytest.fixture
def reservation(member, schedule):
    return Reservation.objects.create(
        member=member,
        schedule=schedule,
        status=member_constants.RESERVATION_STATUS_RESERVED,
        spot=7,
        notes="",
    )


@pytest.fixture
def coach_client(api_client, coach_user, instructor):
    token = ExpiringToken.objects.create(user=coach_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestCoachPermissions:
    def test_unauthenticated_is_401(self, api_client):
        response = api_client.get(reverse("coach:me"))
        assert response.status_code == 401

    def test_non_instructor_is_403(self, api_client, member_user, member):
        token = ExpiringToken.objects.create(user=member_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get(reverse("coach:me"))
        assert response.status_code == 403

    def test_staff_without_instructor_is_403(self, api_client):
        staff = User.objects.create_user(
            username="staffonly",
            password="pass1234",
            is_staff=True,
            is_superuser=True,
        )
        token = ExpiringToken.objects.create(user=staff)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get(reverse("coach:me"))
        assert response.status_code == 403


@pytest.mark.django_db
class TestCoachMe:
    def test_patch_specialties(self, coach_client, instructor):
        response = coach_client.patch(
            reverse("coach:me"),
            data={"specialties": ["HIIT", "Climb"], "unknown": "ignored"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["specialties"] == ["HIIT", "Climb"]
        instructor.refresh_from_db()
        assert instructor.specialties == ["HIIT", "Climb"]


@pytest.mark.django_db
class TestCoachTodayAndSchedules:
    def test_today_and_schedules_are_scoped(self, coach_client, schedule, other_instructor, room):
        Schedule.objects.create(
            title="Other class",
            instructor=other_instructor,
            start_time=schedule.start_time,
            duration_minutes=45,
            room=room,
            status=schedule_constants.SCHEDULE_STATUS_SCHEDULED,
        )
        today = coach_client.get(reverse("coach:today"), {"date": "2026-08-22"})
        assert today.status_code == 200
        assert today.data["date"] == "2026-08-22"
        ids = {item["id"] for item in today.data["classes"]}
        assert str(schedule.id) in ids
        assert len(today.data["classes"]) == 1

        listing = coach_client.get(
            reverse("coach:schedules"),
            {"from": "2026-08-17T00:00:00-04:00", "to": "2026-08-23T23:59:59-04:00"},
        )
        assert listing.status_code == 200
        assert {item["id"] for item in listing.data} == {str(schedule.id)}


@pytest.mark.django_db
class TestCoachCheckInNotesSetup:
    def test_check_in_toggle(self, coach_client, reservation):
        url = reverse("coach:reservation-check-in", kwargs={"reservation_id": reservation.id})
        response = coach_client.patch(url, data={"checked_in": True}, format="json")
        assert response.status_code == 200
        assert response.data["checked_in"] is True
        reservation.refresh_from_db()
        assert reservation.status == member_constants.RESERVATION_STATUS_ATTENDED

        response = coach_client.patch(url, data={"checked_in": False}, format="json")
        assert response.data["checked_in"] is False
        reservation.refresh_from_db()
        assert reservation.status == member_constants.RESERVATION_STATUS_RESERVED

    def test_notes_and_setup_patch(self, coach_client, reservation, member_user):
        notes_url = reverse("coach:reservation-notes", kwargs={"reservation_id": reservation.id})
        notes = coach_client.patch(notes_url, data={"notes": "Lesión de tobillo"}, format="json")
        assert notes.status_code == 200
        assert "Lesión activa" in notes.data["alerts"]

        setup_url = reverse("coach:reservation-setup", kwargs={"reservation_id": reservation.id})
        setup = coach_client.patch(
            setup_url,
            data={"seat_height": 74, "cycling_shoe_size": 42.5},
            format="json",
        )
        assert setup.status_code == 200
        assert setup.data["seat_height"] == 74
        member_user.refresh_from_db()
        assert member_user.seat_height == 74
        assert member_user.cycling_shoe_size == Decimal("42.5")


@pytest.mark.django_db
class TestCoachPlaylist:
    def test_get_empty_and_patch(self, coach_client, schedule):
        url = reverse("coach:class-playlist", kwargs={"class_id": schedule.id})
        empty = coach_client.get(url)
        assert empty.status_code == 200
        assert empty.data["segments"] == []
        assert empty.data["class_id"] == str(schedule.id)

        patched = coach_client.patch(
            url,
            data={
                "title": "Power Ride estándar",
                "segments": [
                    {
                        "name": "Warm-up",
                        "duration_minutes": 8,
                        "bpm_range": "120-128",
                        "tracks": [{"title": "Midnight City", "artist": "M83", "bpm": 105}],
                    }
                ],
            },
            format="json",
        )
        assert patched.status_code == 200
        assert patched.data["segments"][0]["name"] == "Warm-up"
        assert patched.data["segments"][0]["tracks"][0]["title"] == "Midnight City"


@pytest.mark.django_db
class TestCoachStatsAndAuthMe:
    def test_stats_keys(self, coach_client, past_schedule, member, room):
        Reservation.objects.create(
            member=member,
            schedule=past_schedule,
            status=member_constants.RESERVATION_STATUS_ATTENDED,
            spot=1,
        )
        ClassRating.objects.create(schedule=past_schedule, rating=Decimal("4.8"), rating_count=12)
        response = coach_client.get(reverse("coach:stats"), {"months": 6})
        assert response.status_code == 200
        for key in (
            "classes_this_month",
            "total_riders_month",
            "avg_occupancy_pct",
            "avg_rating",
            "rating_count",
            "monthly_classes",
            "monthly_occupancy",
            "monthly_ratings",
            "month_labels",
            "recent_classes",
        ):
            assert key in response.data
        assert len(response.data["month_labels"]) == 6

    def test_is_coach_on_auth_me(self, api_client, coach_user, instructor):
        token = ExpiringToken.objects.create(user=coach_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get(reverse("users:me"))
        assert response.status_code == 200
        assert response.data["is_coach"] is True
