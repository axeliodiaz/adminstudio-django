import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core import signing
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.members import constants
from apps.members.models import Member, Reservation
from apps.members.qr_check_in import QR_TOKEN_SALT, generate_schedule_qr


@pytest.fixture
def graph(db):
    user = get_user_model().objects.create_user("qr-member", password="pass")
    member = Member.objects.create(user=user)
    schedule = baker.make(
        "schedules.Schedule",
        start_time=timezone.now() + datetime.timedelta(minutes=10),
        status="scheduled",
    )
    reservation = Reservation.objects.create(member=member, schedule=schedule, spot=4)
    return user, schedule, reservation


@pytest.mark.django_db
def test_valid_qr_marks_owned_reservation_attended(graph):
    user, schedule, reservation = graph
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        reverse("reservation-qr-check-in", kwargs={"schedule_id": schedule.id}),
        {"token": generate_schedule_qr(schedule)["token"]},
        format="json",
    )
    assert response.status_code == 200
    reservation.refresh_from_db()
    assert reservation.status == constants.RESERVATION_STATUS_ATTENDED
    assert reservation.attendance_method == "qr"
    assert reservation.attended_at is not None


@pytest.mark.django_db
def test_qr_rejects_member_without_reservation(graph):
    _, schedule, reservation = graph
    other = get_user_model().objects.create_user("qr-other", password="pass")
    Member.objects.create(user=other)
    client = APIClient()
    client.force_authenticate(user=other)
    response = client.post(
        reverse("reservation-qr-check-in", kwargs={"schedule_id": schedule.id}),
        {"token": generate_schedule_qr(schedule)["token"]},
        format="json",
    )
    assert response.status_code == 400
    assert "reserva activa" in response.data["detail"]
    reservation.refresh_from_db()
    assert reservation.status == constants.RESERVATION_STATUS_RESERVED


@pytest.mark.django_db
def test_qr_rejects_tampered_and_rotated_tokens(graph):
    user, schedule, reservation = graph
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("reservation-qr-check-in", kwargs={"schedule_id": schedule.id})
    assert client.post(url, {"token": "invalid"}, format="json").status_code == 400
    old_token = generate_schedule_qr(schedule)["token"]
    schedule.check_in_qr_version += 1
    schedule.save(update_fields=["check_in_qr_version"])
    assert client.post(url, {"token": old_token}, format="json").status_code == 400
    reservation.refresh_from_db()
    assert reservation.status == constants.RESERVATION_STATUS_RESERVED


@pytest.mark.django_db
def test_qr_rejects_outside_class_window(graph):
    user, schedule, reservation = graph
    schedule.start_time = timezone.now() + datetime.timedelta(minutes=16)
    schedule.save(update_fields=["start_time"])
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        reverse("reservation-qr-check-in", kwargs={"schedule_id": schedule.id}),
        {"token": generate_schedule_qr(schedule)["token"]},
        format="json",
    )
    assert response.status_code == 400
    assert "15 minutos" in response.data["detail"]
    reservation.refresh_from_db()
    assert reservation.status == constants.RESERVATION_STATUS_RESERVED


@pytest.mark.django_db
def test_admin_can_generate_and_rotate_qr(graph):
    _, schedule, _ = graph
    admin = get_user_model().objects.create_superuser("qr-admin", password="pass")
    client = APIClient()
    client.force_authenticate(user=admin)
    url = reverse("admin-schedule-check-in-qr", kwargs={"schedule_id": schedule.id})
    first = client.get(url)
    rotated = client.post(url)
    assert first.status_code == 200
    assert rotated.status_code == 200
    assert first.data["url"].startswith("http://localhost:5173/#check-in/")
    assert first.data["token"] != rotated.data["token"]
    old_payload = signing.loads(first.data["token"], salt=QR_TOKEN_SALT)
    assert old_payload["version"] == 1
