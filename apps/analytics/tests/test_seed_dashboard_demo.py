"""Tests for dashboard / member-stats demo seeding."""

from datetime import date, datetime, timezone as dt_timezone

import pytest
from django.conf import settings
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


def test_demo_horizon_end_covers_february_next_year():
    assert demo_horizon_end(date(2026, 8, 22)) == date(2027, 2, 28)
    assert demo_horizon_end(date(2026, 10, 31)) == date(2027, 2, 28)
    assert demo_horizon_end(date(2027, 1, 1)) == date(2028, 2, 29)


def test_demo_history_start_is_last_january():
    assert demo_history_start(date(2026, 8, 22)) == date(2025, 1, 1)
    assert demo_history_start(date(2026, 1, 3)) == date(2025, 1, 1)


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


@pytest.mark.django_db
def test_seed_dashboard_demo_gives_every_user_independent_stats():
    staff = User.objects.create_user(
        username="instructor.camila",
        email=f"instructor.camila@{settings.EMAIL_DOMAIN}",
        password="pass1234",
        first_name="Camila",
        last_name="Rojas",
        is_staff=True,
    )
    rider_a = User.objects.create_user(
        username="ana.bravo",
        email=f"member.017@{settings.EMAIL_DOMAIN}",
        password="pass1234",
        first_name="Ana",
        last_name="Bravo",
    )
    rider_b = User.objects.create_user(
        username="axel.diaz",
        email="diaz.axelio@gmail.com",
        password="pass1234",
        first_name="Axel",
        last_name="Díaz",
        is_staff=True,
        is_superuser=True,
    )
    Member.objects.create(user=rider_a)

    call_command(
        "seed_dashboard_demo",
        history_days=21,
        until="2026-09-05",
        as_of="2026-08-22",
        verbosity=0,
    )

    now = datetime(2026, 8, 22, 15, 0, tzinfo=dt_timezone.utc)
    assert Member.objects.filter(user=staff).exists()
    payloads = []
    for user in (staff, rider_a, rider_b, User.objects.get(username=DEMO_RIDER_USERNAME)):
        payload = get_member_stats(user, now=now)
        assert payload["classes_attended_total"] > 0, user.username
        assert payload["favorite_instructor"], user.username
        assert payload["favorite_classes"], user.username
        payloads.append(payload)

    favorites = {row["favorite_instructor"]["first_name"] for row in payloads}
    attended = {row["classes_attended_total"] for row in payloads}
    hours = {tuple(row["preferred_hours"]["values"]) for row in payloads}
    assert len(favorites) > 1 or len(attended) > 1 or len(hours) > 1

    demo_member = User.objects.get(username="taylor.swift")
    demo_payload = get_member_stats(demo_member, now=now)
    assert demo_payload["classes_attended_total"] > 0
