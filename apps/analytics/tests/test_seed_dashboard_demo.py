"""Tests for dashboard / member-stats demo seeding."""

from datetime import date, datetime, timezone as dt_timezone

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.analytics.management.commands.seed_dashboard_demo import (
    DEMO_CLASS_DESCRIPTION,
    DEMO_RIDER_USERNAME,
    demo_history_start,
    demo_horizon_end,
)
from apps.analytics.member_stats import get_member_stats
from apps.members.models import Member, Reservation
from apps.schedules.models import Schedule

User = get_user_model()


def test_demo_horizon_end_covers_october():
    assert demo_horizon_end(date(2026, 8, 22)) == date(2026, 10, 31)
    assert demo_horizon_end(date(2026, 10, 31)) == date(2026, 10, 31)
    assert demo_horizon_end(date(2026, 11, 1)) == date(2027, 10, 31)


def test_demo_history_start_is_six_calendar_months():
    assert demo_history_start(date(2026, 8, 22)) == date(2026, 3, 1)


@pytest.mark.django_db
def test_seed_dashboard_demo_fills_member_charts_through_until():
    existing = User.objects.create_user(
        username="axeldiaz",
        email="axel@example.com",
        password="pass1234",
        first_name="Axel",
        last_name="Díaz",
    )
    Member.objects.create(user=existing)

    call_command(
        "seed_dashboard_demo",
        history_days=10,
        until="2026-09-05",
        as_of="2026-08-22",
        verbosity=0,
    )

    last = (
        Schedule.objects.filter(description=DEMO_CLASS_DESCRIPTION).order_by("-start_time").first()
    )
    assert last is not None
    assert last.start_time.date() == date(2026, 9, 5)
    assert Reservation.objects.filter(spot__isnull=False).exists()

    now = datetime(2026, 8, 22, 15, 0, tzinfo=dt_timezone.utc)
    rider = User.objects.get(username=DEMO_RIDER_USERNAME)
    payload = get_member_stats(rider, now=now)
    assert payload["classes_attended_total"] > 0
    assert payload["top_instructors"]
    assert payload["favorite_classes"]
    assert sum(payload["preferred_hours"]["values"]) == payload["classes_attended_total"]
    assert payload["favorite_spots"]
    assert payload["class_credits"] == 5

    real_payload = get_member_stats(existing, now=now)
    assert real_payload["classes_attended_total"] > 0
    assert real_payload["top_instructors"]

    call_command(
        "seed_dashboard_demo",
        history_days=10,
        until="2026-09-05",
        as_of="2026-08-22",
        verbosity=0,
    )
    second = get_member_stats(existing, now=now)
    assert second["classes_attended_total"] == real_payload["classes_attended_total"]
