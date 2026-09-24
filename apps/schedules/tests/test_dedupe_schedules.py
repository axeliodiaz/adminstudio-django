from datetime import datetime, timedelta, timezone

import pytest
from django.core.management import call_command
from model_bakery import baker

from apps.members.models import Reservation
from apps.schedules.models import Schedule

BASE = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)


def make_schedule(room, instructor, title, start):
    return baker.make(
        "schedules.Schedule",
        room=room,
        instructor=instructor,
        title=title,
        start_time=start,
        status="scheduled",
    )


def make_reservation(schedule):
    return baker.make("members.Reservation", schedule=schedule, member=baker.make("members.Member"))


@pytest.fixture
def duplicate_pair(room_main, instructor_alice):
    first = make_schedule(room_main, instructor_alice, "Sunrise Ride", BASE)
    second = make_schedule(room_main, instructor_alice, "Sunrise Ride", BASE)
    return first, second


@pytest.mark.django_db
class TestDedupeSchedules:
    def test_dry_run_does_not_delete(self, duplicate_pair):
        first, second = duplicate_pair
        call_command("dedupe_schedules")
        assert Schedule.objects.filter(id__in=[first.id, second.id]).count() == 2

    def test_apply_keeps_copy_with_most_reservations(self, duplicate_pair):
        first, second = duplicate_pair
        make_reservation(first)
        make_reservation(second)
        make_reservation(second)
        call_command("dedupe_schedules", apply=True)
        assert Schedule.objects.filter(id=second.id).exists()
        assert not Schedule.objects.filter(id=first.id).exists()
        assert Reservation.objects.filter(schedule_id=second.id).count() == 2
        assert Reservation.objects.filter(schedule_id=first.id).count() == 0

    def test_apply_tie_keeps_oldest(self, duplicate_pair):
        first, second = duplicate_pair
        call_command("dedupe_schedules", apply=True)
        assert Schedule.objects.filter(id=first.id).exists()
        assert not Schedule.objects.filter(id=second.id).exists()

    def test_singles_and_distinct_classes_untouched(self, room_main, instructor_alice):
        solo = make_schedule(room_main, instructor_alice, "Solo Ride", BASE + timedelta(hours=2))
        other_title = make_schedule(room_main, instructor_alice, "Other Ride", BASE)
        call_command("dedupe_schedules", apply=True)
        assert Schedule.objects.filter(id__in=[solo.id, other_title.id]).count() == 2
