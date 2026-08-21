"""Tests for member profile statistics."""

from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from model_bakery import baker

from apps.analytics.member_stats import get_member_stats
from apps.members import constants as member_constants
from apps.members.models import Member
from apps.schedules import constants as schedule_constants
from apps.wallets.models import PlanPurchase, Wallet

User = get_user_model()


def _schedule(*, instructor, room, start, duration=45, title="RIDE 45"):
    return baker.make(
        "schedules.Schedule",
        title=title,
        instructor=instructor,
        room=room,
        status=schedule_constants.SCHEDULE_STATUS_COMPLETED,
        start_time=start,
        duration_minutes=duration,
    )


def _attend(member, schedule, status=member_constants.RESERVATION_STATUS_ATTENDED):
    return baker.make(
        "members.Reservation",
        member=member,
        schedule=schedule,
        status=status,
    )


@pytest.mark.django_db
class TestMemberStatsView:
    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse("member-stats"))
        assert response.status_code == 401

    def test_returns_empty_stats_without_member(self, api_client):
        user = User.objects.create_user(username="nomember", password="pass1234")
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get(reverse("member-stats"))
        assert response.status_code == 200
        assert response.data["classes_completed"] == 0
        assert response.data["favorite_instructor"] is None
        assert len(response.data["monthly_classes"]) == 6
        assert len(response.data["weekly_streak"]) == 4


@pytest.mark.django_db
def test_member_stats_aggregates_attendance_plan_and_favorite():
    now = datetime(2026, 8, 20, 15, 0, tzinfo=dt_timezone.utc)
    today = now.date()
    member_user = baker.make(User, username="rider", first_name="María", last_name="González")
    member = Member.objects.create(user=member_user)

    favorite_user = baker.make(User, first_name="Tomás", last_name="Muñoz")
    favorite = baker.make(
        "instructors.Instructor",
        user=favorite_user,
        tagline="Power Ride • HIIT cycling",
        instagram_username="tomasride",
    )
    other = baker.make(
        "instructors.Instructor",
        user=baker.make(User, first_name="Camila", last_name="Rojas"),
    )
    studio = baker.make("studios.Studio", name="PulseFit Patio Andino", is_active=True)
    room = baker.make("studios.Room", studio=studio, capacity=20, is_active=True)

    plan = baker.make("plans.Plan", name="Starter 8", classes_included=8, price=59000)
    Wallet.objects.create(user=member_user, is_unlimited_membership_active=False)
    PlanPurchase.objects.create(
        user=member_user,
        plan=plan,
        price_paid=Decimal("59000.00"),
        activated_since=today - timedelta(days=10),
    )

    # Three consecutive ISO weeks ending last week (current week empty → streak 3).
    last_monday = today - timedelta(days=today.weekday())
    for weeks_ago in (1, 2, 3):
        day = last_monday - timedelta(weeks=weeks_ago)
        start = datetime(day.year, day.month, day.day, 18, 0, tzinfo=dt_timezone.utc)
        _attend(member, _schedule(instructor=favorite, room=room, start=start))

    extra_day = last_monday - timedelta(weeks=1, days=1)
    extra_start = datetime(
        extra_day.year, extra_day.month, extra_day.day, 10, 0, tzinfo=dt_timezone.utc
    )
    _attend(member, _schedule(instructor=favorite, room=room, start=extra_start, duration=50))

    other_day = last_monday - timedelta(weeks=1, days=2)
    other_start = datetime(
        other_day.year, other_day.month, other_day.day, 12, 0, tzinfo=dt_timezone.utc
    )
    _attend(member, _schedule(instructor=other, room=room, start=other_start))

    july = datetime(2026, 7, 2, 19, 0, tzinfo=dt_timezone.utc)
    _attend(member, _schedule(instructor=favorite, room=room, start=july, duration=45))

    this_month_reserved = datetime(2026, 8, 18, 19, 0, tzinfo=dt_timezone.utc)
    _attend(
        member,
        _schedule(instructor=favorite, room=room, start=this_month_reserved),
        status=member_constants.RESERVATION_STATUS_RESERVED,
    )

    payload = get_member_stats(member_user, now=now)

    assert payload["plan_name"] == "Starter 8"
    assert payload["classes_included"] == 8
    assert payload["is_unlimited"] is False
    assert payload["preferred_studio"] == "PulseFit Patio Andino"
    assert payload["current_streak_weeks"] == 3
    assert payload["weekly_streak"] == [True, True, True, False]
    assert payload["last_visit"] == "2026-08-10"
    assert payload["classes_this_month"] == 5
    assert payload["favorite_instructor"]["first_name"] == "Tomás"
    assert payload["favorite_instructor"]["instagram_username"] == "tomasride"
    assert payload["classes_completed"] == sum(payload["monthly_classes"])
    assert payload["total_ride_minutes"] > 0
    assert payload["monthly_labels"][-1] == "2026-08"
