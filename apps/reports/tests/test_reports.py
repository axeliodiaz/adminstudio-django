"""Tests for the precomputed reports module (CYC-441, CYC-442)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from drf_expiring_token.models import ExpiringToken
from model_bakery import baker

from apps.members import constants as member_constants
from apps.members.models import Member, Reservation
from apps.reports import services
from apps.reports.models import ClassMetrics, DailyMetrics
from apps.schedules import constants as schedule_constants

User = get_user_model()


@pytest.fixture
def admin_client(api_client):
    admin = User.objects.create_user(
        username="reports.admin",
        email="reports.admin@example.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
    )
    token = ExpiringToken.objects.create(user=admin)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def member_client(api_client):
    member = User.objects.create_user(
        username="reports.member",
        email="reports.member@example.com",
        password="testpass123",
    )
    token = ExpiringToken.objects.create(user=member)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


def _make_class(start_time, capacity=10, status=schedule_constants.SCHEDULE_STATUS_SCHEDULED):
    room = baker.make("studios.Room", capacity=capacity, is_active=True)
    instructor = baker.make("instructors.Instructor")
    return baker.make(
        "schedules.Schedule",
        room=room,
        instructor=instructor,
        start_time=start_time,
        status=status,
    )


def _book(member, schedule, status=member_constants.RESERVATION_STATUS_ATTENDED):
    return baker.make("members.Reservation", member=member, schedule=schedule, status=status)


@pytest.mark.django_db
class TestRecompute:
    def test_reservation_save_updates_daily_and_class_rows(self):
        member = baker.make("members.Member")
        start = timezone.now() - timedelta(days=1)
        schedule = _make_class(start)
        _book(member, schedule)

        row = DailyMetrics.objects.get(date=start.date(), studio__isnull=True)
        assert row.reservations_booked == 1
        assert row.reservations_attended == 1
        assert row.occupancy_rate == 10.0
        assert row.attendee_ids == [str(member.id)]

        class_row = ClassMetrics.objects.get(schedule=schedule)
        assert class_row.booked == 1
        assert class_row.attended == 1
        assert class_row.capacity == 10

    def test_status_change_is_reflected(self):
        member = baker.make("members.Member")
        start = timezone.now() - timedelta(days=1)
        schedule = _make_class(start)
        reservation = _book(member, schedule)
        reservation.status = member_constants.RESERVATION_STATUS_MISSED
        reservation.save()

        row = DailyMetrics.objects.get(date=start.date(), studio__isnull=True)
        assert row.reservations_attended == 0
        assert row.reservations_missed == 1
        assert row.attendee_ids == []

    def test_canceled_class_excluded_from_capacity(self):
        start = timezone.now() - timedelta(days=1)
        _make_class(start, status=schedule_constants.SCHEDULE_STATUS_CANCELED)
        row = DailyMetrics.objects.get(date=start.date(), studio__isnull=True)
        assert row.classes_canceled == 1
        assert row.spots_capacity == 0

    def test_purchase_updates_commercial_half(self):
        plan = baker.make("plans.Plan", name="Pack 10", price=100_000)
        today = timezone.localdate()
        baker.make("wallets.PlanPurchase", plan=plan, price_paid=90_000, discount_amount=10_000)

        row = DailyMetrics.objects.get(date=today, studio__isnull=True)
        assert row.purchases_count == 1
        assert float(row.revenue) == 90_000
        assert float(row.discount_total) == 10_000
        assert row.first_time_buyers == 1
        assert row.revenue_by_plan == {"Pack 10": {"revenue": 90_000.0, "count": 1}}

    def test_returning_buyer_detection(self):
        plan = baker.make("plans.Plan", price=50_000)
        user = baker.make("users.User")
        old_purchase = baker.make("wallets.PlanPurchase", user=user, plan=plan, price_paid=50_000)
        old = timezone.now() - timedelta(days=10)
        # AutoCreatedField ignores the value at creation; set it via update().
        type(old_purchase).objects.filter(pk=old_purchase.pk).update(created=old)
        baker.make("wallets.PlanPurchase", user=user, plan=plan, price_paid=50_000)

        today = timezone.localdate()
        row = DailyMetrics.objects.get(date=today, studio__isnull=True)
        assert row.first_time_buyers == 0
        assert row.returning_buyers == 1

    def test_refresh_all_rebuilds_history(self):
        member = baker.make("members.Member")
        old_day = timezone.now() - timedelta(days=5)
        schedule = _make_class(old_day)
        _book(member, schedule)
        DailyMetrics.objects.all().delete()
        ClassMetrics.objects.all().delete()

        summary = services.refresh_all()
        assert summary["days_recomputed"] >= 5
        row = DailyMetrics.objects.get(date=old_day.date(), studio__isnull=True)
        assert row.reservations_attended == 1

    def test_soft_removed_reservation_does_not_count(self):
        member = baker.make("members.Member")
        start = timezone.now() - timedelta(days=1)
        schedule = _make_class(start)
        reservation = _book(member, schedule)
        reservation.delete()  # soft delete

        row = DailyMetrics.objects.get(date=start.date(), studio__isnull=True)
        assert row.reservations_attended == 0


@pytest.mark.django_db
class TestApi:
    def test_anonymous_gets_401(self, api_client):
        assert api_client.get(reverse("reports-catalog")).status_code == 401

    def test_member_gets_403(self, member_client):
        assert member_client.get(reverse("reports-catalog")).status_code == 403

    def test_plain_staff_gets_403(self, api_client):
        staff = User.objects.create_user(username="plain.staff", password="pass1234", is_staff=True)
        token = ExpiringToken.objects.create(user=staff)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        assert api_client.get(reverse("reports-catalog")).status_code == 403

    def test_catalog_lists_reports(self, admin_client):
        response = admin_client.get(reverse("reports-catalog"))
        assert response.status_code == 200
        keys = {report["key"] for report in response.data["reports"]}
        assert {
            "attendance",
            "occupancy",
            "revenue",
            "retention",
            "waitlist",
            "instructors",
            "promotions",
            "communications",
        } <= keys

    def test_unknown_report_404(self, admin_client):
        response = admin_client.get(reverse("reports-detail", kwargs={"report_key": "nope"}))
        assert response.status_code == 404

    def test_attendance_report_payload(self, admin_client):
        member = baker.make("members.Member")
        start = timezone.now() - timedelta(days=1)
        schedule = _make_class(start)
        _book(member, schedule)

        response = admin_client.get(reverse("reports-detail", kwargs={"report_key": "attendance"}))
        assert response.status_code == 200
        assert response.data["totals"]["attended"] == 1
        assert response.data["totals"]["attendance_rate"] == 100.0
        day = next(
            item for item in response.data["series"] if item["date"] == start.date().isoformat()
        )
        assert day["attended"] == 1

    def test_retention_report_counts_new_riders(self, admin_client):
        member = baker.make("members.Member")
        schedule = _make_class(timezone.now() - timedelta(days=1))
        _book(member, schedule)

        response = admin_client.get(reverse("reports-detail", kwargs={"report_key": "retention"}))
        assert response.status_code == 200
        assert response.data["active_riders"] == 1
        assert response.data["new_riders"] == 1
        assert response.data["returning_riders"] == 0

    def test_refresh_endpoint_rebuilds(self, admin_client):
        member = baker.make("members.Member")
        schedule = _make_class(timezone.now() - timedelta(days=1))
        _book(member, schedule)
        DailyMetrics.objects.all().delete()

        response = admin_client.post(reverse("reports-refresh"))
        assert response.status_code == 200
        assert response.data["days_recomputed"] >= 1
        assert DailyMetrics.objects.filter(reservations_attended=1).exists()

    def test_refresh_endpoint_requires_admin(self, member_client):
        assert member_client.post(reverse("reports-refresh")).status_code == 403
