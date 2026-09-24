"""Mis reservas payload embeds class details in one query (CYC-81)."""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.instructors.models import Instructor
from apps.members.models import Member, Reservation
from apps.members.services import list_reservations
from apps.schedules.models import Schedule
from apps.studios.models import Address, Room, Studio

User = get_user_model()


def _user(prefix, **extra):
    return User.objects.create_user(
        username=f"{prefix}_{uuid.uuid4().hex[:8]}",
        email=f"{prefix}_{uuid.uuid4().hex[:8]}@ex.com",
        password="pass",
        **extra,
    )


@pytest.fixture
def graph():
    member = Member.objects.create(user=_user("member"))
    studio = Studio.objects.create(
        name="PulseFit", address=Address.objects.create(address="Main 1"), is_active=True
    )
    room = Room.objects.create(studio=studio, name="Sala A", capacity=20, is_active=True)
    instructor = Instructor.objects.create(
        user=_user("coach", first_name="Kristina", last_name="Girod")
    )
    start = (timezone.now() + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    schedules = [
        Schedule.objects.create(
            title=f"Ride {i}",
            instructor=instructor,
            room=room,
            start_time=start + timedelta(hours=i),
            duration_minutes=45,
            status="scheduled",
        )
        for i in range(3)
    ]
    for i, schedule in enumerate(schedules):
        Reservation.objects.create(member=member, schedule=schedule, spot=i + 1)
    return member, studio, room, instructor, schedules


@pytest.mark.django_db
class TestMemberReservationPayload:
    def test_embeds_schedule_room_studio_and_instructor(self, graph, django_assert_num_queries):
        member, studio, room, instructor, schedules = graph
        day = schedules[0].start_time.date()
        with django_assert_num_queries(1):
            rows = list_reservations(
                {"start_date": day, "end_date": day, "member_id": str(member.id)},
                include_schedule=True,
            )
        assert len(rows) == 3
        first = sorted(rows, key=lambda r: r.schedule.start_time)[0]
        assert first.schedule.id == schedules[0].id
        assert first.schedule.title == "Ride 0"
        assert first.schedule.duration_minutes == 45
        assert first.schedule.room_id == room.id
        assert first.schedule.room_name == "Sala A"
        assert first.schedule.studio_id == studio.id
        assert first.schedule.studio_name == "PulseFit"
        assert first.schedule.instructor_id == instructor.id
        assert first.schedule.instructor_name == "Kristina Girod"

    def test_default_payload_is_unchanged(self, graph):
        member, *_, schedules = graph
        day = schedules[0].start_time.date()
        rows = list_reservations({"start_date": day, "end_date": day, "member_id": str(member.id)})
        assert "schedule" not in rows[0].model_dump()

    def test_member_endpoint_returns_embedded_schedule(self, graph):
        member, *_ = graph
        client = APIClient()
        client.force_authenticate(user=member.user)
        resp = client.get(reverse("reservations"))
        assert resp.status_code == 200
        assert len(resp.data) == 3
        assert resp.data[0]["schedule"]["room_name"] == "Sala A"
        assert resp.data[0]["schedule"]["studio_name"] == "PulseFit"
