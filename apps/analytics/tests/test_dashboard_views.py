"""API tests for the staff admin dashboard."""

from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from model_bakery import baker

from apps.analytics.constants import CLP_PER_MXN, CLP_PER_USD
from apps.analytics.services import get_admin_dashboard
from apps.members import constants as member_constants
from apps.members.models import Member
from apps.schedules import constants as schedule_constants
from apps.wallets.models import PlanPurchase, Wallet

User = get_user_model()


@pytest.fixture
def staff_client(api_client):
    staff_user = User.objects.create_user(
        username="dashadmin",
        email="dashadmin@example.com",
        password="testpass123",
        is_staff=True,
    )
    token = ExpiringToken.objects.create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestAdminDashboardView:
    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse("admin-dashboard"))
        assert response.status_code == 401

    def test_requires_staff(self, api_client):
        user = User.objects.create_user(username="memberdash", password="pass1234")
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get(reverse("admin-dashboard"))
        assert response.status_code == 403

    def test_returns_payload_for_staff(self, staff_client):
        response = staff_client.get(reverse("admin-dashboard"))
        assert response.status_code == 200
        body = response.data
        assert "kpis" in body
        assert "reservations_30d" in body
        assert "revenue_by_plan" in body
        assert "purchases_30d" in body
        assert "recent_purchases" in body
        assert "purchases_7d" in body["kpis"]
        assert set(body["kpis"]["revenue_7d"]).issuperset(
            {"amount_clp", "amount_usd", "amount_mxn", "fx"}
        )
        assert body["range"]["days"] == 30
        assert len(body["reservations_30d"]["labels"]) == 30

    def test_days_query_param_shortens_series(self, staff_client):
        response = staff_client.get(reverse("admin-dashboard"), {"days": 7})
        assert response.status_code == 200
        body = response.data
        assert body["range"]["days"] == 7
        assert len(body["reservations_30d"]["labels"]) == 7
        assert len(body["purchases_30d"]["labels"]) == 7
        assert len(body["classes_vs_noshows"]["labels"]) == 7

    def test_invalid_days_falls_back_to_default(self, staff_client):
        response = staff_client.get(reverse("admin-dashboard"), {"days": 11})
        assert response.status_code == 200
        assert response.data["range"]["days"] == 30


@pytest.mark.django_db
def test_dashboard_aggregates_occupancy_and_fx():
    now = datetime(2026, 8, 19, 15, 0, tzinfo=dt_timezone.utc)
    today = now.date()
    instructor = baker.make(
        "instructors.Instructor",
        user__first_name="Camila",
        user__last_name="Rojas",
    )
    room = baker.make("studios.Room", capacity=10, is_active=True)
    this_week = baker.make(
        "schedules.Schedule",
        title="RIDE 45",
        instructor=instructor,
        room=room,
        status=schedule_constants.SCHEDULE_STATUS_COMPLETED,
        start_time=datetime(today.year, today.month, today.day, 18, 0, tzinfo=dt_timezone.utc),
    )
    last_week_day = today - timedelta(days=8)
    last_week = baker.make(
        "schedules.Schedule",
        title="YOGA 45",
        instructor=instructor,
        room=room,
        status=schedule_constants.SCHEDULE_STATUS_COMPLETED,
        start_time=datetime(
            last_week_day.year,
            last_week_day.month,
            last_week_day.day,
            10,
            0,
            tzinfo=dt_timezone.utc,
        ),
    )

    for _ in range(8):
        baker.make(
            "members.Reservation",
            schedule=this_week,
            status=member_constants.RESERVATION_STATUS_ATTENDED,
        )
    for _ in range(5):
        baker.make(
            "members.Reservation",
            schedule=last_week,
            status=member_constants.RESERVATION_STATUS_ATTENDED,
        )

    member_user = baker.make(User, is_active=True)
    Member.objects.create(user=member_user)
    Wallet.objects.create(
        user=member_user,
        active_membership_end_date=today + timedelta(days=10),
    )
    plan = baker.make("plans.Plan", name="Ilimitado", price=89000)
    purchase = PlanPurchase.objects.create(
        user=member_user,
        plan=plan,
        price_paid=Decimal("89000.00"),
        activated_since=today,
    )
    PlanPurchase.objects.filter(pk=purchase.pk).update(created=now)

    payload = get_admin_dashboard(now=now)

    assert payload["kpis"]["weekly_occupancy"]["value"] == 80.0
    assert payload["kpis"]["weekly_occupancy"]["delta_pp"] == 30.0
    assert payload["kpis"]["reservations_today"]["value"] == 8
    assert payload["kpis"]["active_members"]["value"] == 1
    assert payload["kpis"]["revenue_7d"]["amount_clp"] == 89000.0
    assert payload["kpis"]["revenue_7d"]["amount_usd"] == round(89000 / CLP_PER_USD, 2)
    assert payload["kpis"]["revenue_7d"]["amount_mxn"] == round(89000 / CLP_PER_MXN, 2)
    assert payload["occupancy_by_instructor"][0]["name"] == "Camila R."
    assert payload["demand_by_format"][0]["format"] == "RIDE"
    ride = next(row for row in payload["demand_by_format"] if row["format"] == "RIDE")
    yoga = next(row for row in payload["demand_by_format"] if row["format"] == "YOGA")
    assert ride["occupancy"] == 80.0
    assert yoga["occupancy"] == 50.0
    assert payload["plan_mix"][0]["plan"] == "Ilimitado"
