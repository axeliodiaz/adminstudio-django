"""Tests for coach demo seeding."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.coach.constants import DEMO_CLASS_DESCRIPTION, DEMO_SHOWCASE_USERNAME
from apps.coach.management.commands.seed_coach_demo import coach_seed_end, coach_seed_start
from apps.coach.models import ClassPlaylist, PlaylistTrack
from apps.coach.services import get_playlist, get_roster, get_stats, get_today, list_schedules
from apps.instructors.models import Instructor
from apps.members.models import Reservation
from apps.schedules.models import Schedule

User = get_user_model()
SANTIAGO = ZoneInfo("America/Santiago")


def test_coach_seed_horizon():
    assert coach_seed_start(date(2026, 8, 23)) == date(2025, 1, 1)
    assert coach_seed_end(date(2026, 8, 23)) == date(2027, 2, 28)
    assert coach_seed_start(date(2026, 1, 3)) == date(2025, 1, 1)
    assert coach_seed_end(date(2027, 1, 1)) == date(2028, 2, 29)


@pytest.mark.django_db
def test_seed_coach_demo_fills_existing_instructor_week_including_sunday():
    axel = User.objects.create_user(
        username="axelio",
        email="diaz.axelio@gmail.com",
        password="pass1234",
        first_name="Axel",
        last_name="Díaz",
        is_staff=True,
        is_superuser=True,
    )
    instructor = Instructor.objects.create(user=axel, tagline="Ride")

    call_command(
        "seed_coach_demo",
        as_of="2026-08-23",
        from_date="2026-08-17",
        until="2026-08-23",
        verbosity=0,
    )

    sunday = get_today(instructor, "2026-08-23")
    assert sunday["classes"], "Sunday should have classes for Clases del día"
    week = list_schedules(
        instructor,
        datetime(2026, 8, 17, 0, 0, tzinfo=SANTIAGO).isoformat(),
        datetime(2026, 8, 23, 23, 59, tzinfo=SANTIAGO).isoformat(),
    )
    assert len(week) >= 2
    assert Schedule.objects.filter(
        instructor=instructor, description=DEMO_CLASS_DESCRIPTION
    ).exists()

    first = sunday["classes"][0]
    roster = get_roster(instructor, first["id"])
    assert roster["riders"]
    assert any(rider["spot_number"] for rider in roster["riders"])
    playlist = get_playlist(instructor, first["id"])
    assert playlist["segments"]
    assert PlaylistTrack.objects.filter(segment__playlist__schedule_id=first["id"]).exists()
    assert Reservation.objects.filter(schedule_id=first["id"]).exclude(notes="").exists()

    stats = get_stats(instructor, months=6)
    assert "monthly_classes" in stats
    assert "recent_classes" in stats

    tomas = User.objects.get(username="tomasride")
    kristina = User.objects.get(username=DEMO_SHOWCASE_USERNAME)
    assert Instructor.objects.filter(user=tomas).exists()
    assert kristina.first_name == "Kristina"
    assert kristina.last_name == "Girod"
    assert axel.first_name == "Axel"
    assert axel.last_name == "Díaz"
    assert ClassPlaylist.objects.filter(instructor=instructor).exists()

    first_count = Schedule.objects.filter(
        instructor=instructor, description=DEMO_CLASS_DESCRIPTION
    ).count()
    call_command(
        "seed_coach_demo",
        as_of="2026-08-23",
        from_date="2026-08-17",
        until="2026-08-23",
        verbosity=0,
    )
    assert (
        Schedule.objects.filter(instructor=instructor, description=DEMO_CLASS_DESCRIPTION).count()
        == first_count
    )
