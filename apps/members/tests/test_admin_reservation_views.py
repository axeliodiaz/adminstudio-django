"""API tests for staff admin reservation endpoints."""

from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from model_bakery import baker
from rest_framework import status

from apps.members import constants as member_constants
from apps.members.models import Member, Reservation

User = get_user_model()


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="reservationadmin",
        email="reservationadmin@example.com",
        password="pass1234",
        is_staff=True,
    )


@pytest.fixture
def staff_client(api_client, staff_user):
    token = ExpiringToken.objects.create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def reservation_graph(db):
    instructor = baker.make(
        "instructors.Instructor",
        user__username="coach",
        user__email="coach@example.com",
        user__first_name="Coach",
        user__last_name="One",
    )
    room = baker.make("studios.Room", name="Sala A", capacity=20)
    schedule = baker.make(
        "schedules.Schedule",
        title="RIDE 45",
        instructor=instructor,
        room=room,
        start_time=datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc),
        duration_minutes=45,
        status="scheduled",
    )
    user = User.objects.create_user(
        username="socio@example.com",
        email="socio@example.com",
        password="pass1234",
        first_name="Ana",
        last_name="Ríos",
    )
    member = Member.objects.create(user=user)
    reservation = Reservation.objects.create(
        member=member,
        schedule=schedule,
        spot=3,
        status=member_constants.RESERVATION_STATUS_RESERVED,
        notes="Walk-in",
    )
    return {
        "instructor": instructor,
        "room": room,
        "schedule": schedule,
        "user": user,
        "member": member,
        "reservation": reservation,
    }


@pytest.mark.django_db
class TestAdminReservationViews:
    def test_list_requires_staff(self, api_client, reservation_graph):
        user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="pass1234",
        )
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("admin-reservation-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_returns_enriched_rows(self, staff_client, reservation_graph):
        reservation = reservation_graph["reservation"]
        response = staff_client.get(
            reverse("admin-reservation-list"),
            {
                "start_date": "2025-06-01",
                "end_date": "2025-06-07",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        row = response.data[0]
        assert row["id"] == str(reservation.id)
        assert row["member_email"] == "socio@example.com"
        assert row["member_name"] == "Ana Ríos"
        assert row["schedule_title"] == "RIDE 45"
        assert row["room_name"] == "Sala A"
        assert row["spot"] == 3
        assert row["status"] == member_constants.RESERVATION_STATUS_RESERVED

    def test_list_includes_cancelled_and_filters_status(self, staff_client, reservation_graph):
        reservation = reservation_graph["reservation"]
        reservation.status = member_constants.RESERVATION_STATUS_CANCELLED
        reservation.save(update_fields=["status"])

        all_response = staff_client.get(
            reverse("admin-reservation-list"),
            {"start_date": "2025-06-01", "end_date": "2025-06-07"},
        )
        assert all_response.status_code == status.HTTP_200_OK
        assert len(all_response.data) == 1

        reserved_response = staff_client.get(
            reverse("admin-reservation-list"),
            {
                "start_date": "2025-06-01",
                "end_date": "2025-06-07",
                "status": member_constants.RESERVATION_STATUS_RESERVED,
            },
        )
        assert reserved_response.status_code == status.HTTP_200_OK
        assert reserved_response.data == []

        cancelled_response = staff_client.get(
            reverse("admin-reservation-list"),
            {
                "start_date": "2025-06-01",
                "end_date": "2025-06-07",
                "status": member_constants.RESERVATION_STATUS_CANCELLED,
            },
        )
        assert cancelled_response.status_code == status.HTTP_200_OK
        assert len(cancelled_response.data) == 1

    def test_list_search_by_email(self, staff_client, reservation_graph):
        response = staff_client.get(
            reverse("admin-reservation-list"),
            {
                "start_date": "2025-06-01",
                "end_date": "2025-06-07",
                "search": "socio@",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        miss = staff_client.get(
            reverse("admin-reservation-list"),
            {
                "start_date": "2025-06-01",
                "end_date": "2025-06-07",
                "search": "nobody",
            },
        )
        assert miss.status_code == status.HTTP_200_OK
        assert miss.data == []

    def test_create_cancel_and_change_spot(self, staff_client, reservation_graph):
        from apps.wallets.models import Wallet

        schedule = reservation_graph["schedule"]
        other_user = User.objects.create_user(
            username="otro@example.com",
            email="otro@example.com",
            password="pass1234",
            first_name="Luis",
            last_name="Pérez",
        )
        Wallet.objects.create(user=other_user, class_credits=5)

        create_response = staff_client.post(
            reverse("admin-reservation-list"),
            {
                "user_id": str(other_user.id),
                "schedule_id": str(schedule.id),
                "spot": 7,
                "notes": "Admin booking",
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        assert create_response.data["spot"] == 7
        assert create_response.data["member_email"] == "otro@example.com"
        reservation_id = create_response.data["id"]

        change_response = staff_client.patch(
            reverse("admin-reservation-change-spot", kwargs={"reservation_id": reservation_id}),
            {"new_spot": 8},
            format="json",
        )
        assert change_response.status_code == status.HTTP_200_OK
        assert change_response.data["spot"] == 8

        cancel_response = staff_client.post(
            reverse("admin-reservation-cancel", kwargs={"reservation_id": reservation_id}),
            format="json",
        )
        assert cancel_response.status_code == status.HTTP_200_OK
        assert cancel_response.data["status"] == member_constants.RESERVATION_STATUS_CANCELLED

    def test_detail_not_found(self, staff_client):
        response = staff_client.get(
            reverse(
                "admin-reservation-detail",
                kwargs={"reservation_id": "00000000-0000-0000-0000-000000000001"},
            )
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestAdminAttendanceViews:
    def test_day_list_and_roster(self, staff_client, reservation_graph):
        schedule = reservation_graph["schedule"]
        reservation = reservation_graph["reservation"]

        day = staff_client.get(reverse("admin-attendance-day"), {"date": "2025-06-02"})
        assert day.status_code == status.HTTP_200_OK
        assert day.data["date"] == "2025-06-02"
        assert len(day.data["classes"]) == 1
        row = day.data["classes"][0]
        assert row["id"] == str(schedule.id)
        assert row["pending"] == 1
        assert row["attended"] == 0
        assert row["booked"] == 1

        roster = staff_client.get(
            reverse("admin-attendance-roster", kwargs={"schedule_id": schedule.id})
        )
        assert roster.status_code == status.HTTP_200_OK
        assert len(roster.data["riders"]) == 1
        rider = roster.data["riders"][0]
        assert rider["reservation_id"] == str(reservation.id)
        assert rider["status"] == member_constants.RESERVATION_STATUS_RESERVED
        assert rider["member_email"] == "socio@example.com"

    def test_mark_attended_and_missed_after_class(self, staff_client, reservation_graph):
        reservation = reservation_graph["reservation"]
        url = reverse(
            "admin-reservation-attendance",
            kwargs={"reservation_id": reservation.id},
        )

        attended = staff_client.patch(url, {"status": "ATTENDED"}, format="json")
        assert attended.status_code == status.HTTP_200_OK
        assert attended.data["status"] == member_constants.RESERVATION_STATUS_ATTENDED
        reservation.refresh_from_db()
        assert reservation.status == member_constants.RESERVATION_STATUS_ATTENDED

        missed = staff_client.patch(url, {"status": "MISSED"}, format="json")
        assert missed.status_code == status.HTTP_200_OK
        reservation.refresh_from_db()
        assert reservation.status == member_constants.RESERVATION_STATUS_MISSED

        pending = staff_client.patch(url, {"status": "RESERVED"}, format="json")
        assert pending.status_code == status.HTTP_200_OK
        reservation.refresh_from_db()
        assert reservation.status == member_constants.RESERVATION_STATUS_RESERVED

    def test_cannot_mark_cancelled(self, staff_client, reservation_graph):
        reservation = reservation_graph["reservation"]
        reservation.status = member_constants.RESERVATION_STATUS_CANCELLED
        reservation.save(update_fields=["status"])

        response = staff_client.patch(
            reverse(
                "admin-reservation-attendance",
                kwargs={"reservation_id": reservation.id},
            ),
            {"status": "ATTENDED"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_remaining_missed(self, staff_client, reservation_graph):
        schedule = reservation_graph["schedule"]
        other_user = User.objects.create_user(
            username="otro-asis@example.com",
            email="otro-asis@example.com",
            password="pass1234",
            first_name="Luis",
            last_name="Pérez",
        )
        other_member = Member.objects.create(user=other_user)
        other = Reservation.objects.create(
            member=other_member,
            schedule=schedule,
            spot=4,
            status=member_constants.RESERVATION_STATUS_ATTENDED,
        )

        response = staff_client.post(
            reverse("admin-attendance-mark-missed", kwargs={"schedule_id": schedule.id}),
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["updated"] == 1
        reservation_graph["reservation"].refresh_from_db()
        other.refresh_from_db()
        assert reservation_graph["reservation"].status == member_constants.RESERVATION_STATUS_MISSED
        assert other.status == member_constants.RESERVATION_STATUS_ATTENDED

    def test_attendance_requires_staff(self, api_client, reservation_graph):
        user = User.objects.create_user(
            username="member-attendance",
            email="member-attendance@example.com",
            password="pass1234",
        )
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get(reverse("admin-attendance-day"))
        assert response.status_code == status.HTTP_403_FORBIDDEN
