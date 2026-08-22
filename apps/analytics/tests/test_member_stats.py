"""Tests for member profile statistics."""

from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
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


def _attend(member, schedule, status=member_constants.RESERVATION_STATUS_ATTENDED, spot=None):
    return baker.make(
        "members.Reservation",
        member=member,
        schedule=schedule,
        status=status,
        spot=spot,
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
        assert len(response.data["monthly_classes"]) == timezone.localdate().month
        assert len(response.data["weekly_streak"]) == 4


@pytest.mark.django_db
class TestAdminMemberStatsView:
    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse("admin-member-stats", kwargs={"user_id": uuid4()}))
        assert response.status_code == 401

    def test_requires_staff(self, api_client):
        member_user = User.objects.create_user(username="riderstats", password="pass1234")
        other = User.objects.create_user(username="notstaff", password="pass1234")
        token = ExpiringToken.objects.create(user=other)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get(reverse("admin-member-stats", kwargs={"user_id": member_user.id}))
        assert response.status_code == 403

    def test_returns_target_user_stats_for_staff(self, api_client):
        staff_user = User.objects.create_user(
            username="staffstats",
            password="pass1234",
            is_staff=True,
        )
        member_user = User.objects.create_user(
            username="targetrider",
            password="pass1234",
            first_name="María",
        )
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get(reverse("admin-member-stats", kwargs={"user_id": member_user.id}))
        assert response.status_code == 200
        assert response.data["classes_completed"] == 0
        assert "monthly_classes" in response.data

    def test_returns_404_for_unknown_user(self, api_client):
        staff_user = User.objects.create_user(
            username="staffmissing",
            password="pass1234",
            is_staff=True,
        )
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get(reverse("admin-member-stats", kwargs={"user_id": uuid4()}))
        assert response.status_code == 404


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
    Wallet.objects.create(
        user=member_user,
        is_unlimited_membership_active=False,
        class_credits=3,
        guest_pass_credits=1,
    )
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
        _attend(
            member,
            _schedule(instructor=favorite, room=room, start=start, title="Power Ride"),
            spot=7,
        )

    extra_day = last_monday - timedelta(weeks=1, days=1)
    extra_start = datetime(
        extra_day.year, extra_day.month, extra_day.day, 10, 0, tzinfo=dt_timezone.utc
    )
    _attend(
        member,
        _schedule(
            instructor=favorite, room=room, start=extra_start, duration=50, title="Power Ride"
        ),
        spot=7,
    )

    other_day = last_monday - timedelta(weeks=1, days=2)
    other_start = datetime(
        other_day.year, other_day.month, other_day.day, 12, 0, tzinfo=dt_timezone.utc
    )
    _attend(
        member,
        _schedule(instructor=other, room=room, start=other_start, title="Rhythm Ride"),
        spot=12,
    )

    july = datetime(2026, 7, 2, 19, 0, tzinfo=dt_timezone.utc)
    _attend(
        member,
        _schedule(instructor=favorite, room=room, start=july, duration=45, title="Power Ride"),
        spot=7,
    )

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
    assert payload["monthly_labels"][0] == "2026-01"
    assert payload["monthly_labels"][-1] == "2026-08"
    assert payload["class_credits"] == 3
    assert payload["guest_pass_credits"] == 1
    assert payload["top_instructors"][0]["first_name"] == "Tomás"
    assert payload["top_instructors"][0]["classes"] >= payload["top_instructors"][1]["classes"]
    assert payload["favorite_classes"][0]["name"] == "Power Ride"
    assert payload["favorite_spots"][0]["spot"] == 7
    assert sum(payload["preferred_hours"]["values"]) == payload["classes_attended_total"]
    assert sum(payload["weekday_classes"]) == payload["classes_attended_total"]
    assert payload["rider_persona"] is not None
    assert payload["attendance_rate"] == 100.0
