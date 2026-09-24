"""Room double-booking validation for staff class create/update (CYC-91)."""

from datetime import datetime, timedelta, timezone

import pytest
from model_bakery import baker

from apps.schedules import constants
from apps.schedules.models import Schedule
from apps.schedules.services import create_admin_schedule, update_admin_schedule

BASE = datetime(2030, 1, 7, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def existing(instructor_alice, room_main):
    return baker.make(
        "schedules.Schedule",
        instructor=instructor_alice,
        room=room_main,
        start_time=BASE,
        duration_minutes=45,
        status=constants.SCHEDULE_STATUS_SCHEDULED,
        title="Sunrise Ride",
    )


def _payload(instructor, room, start, **extra):
    data = {
        "title": "Power Ride",
        "instructor_id": instructor.id,
        "room_id": room.id,
        "start_time": start,
        "duration_minutes": 45,
    }
    data.update(extra)
    return data


@pytest.mark.django_db
class TestRoomOverlap:
    def test_create_rejects_overlap_in_same_room(self, existing, instructor_bob, room_main):
        with pytest.raises(ValueError, match="La sala ya tiene una clase"):
            create_admin_schedule(
                data=_payload(instructor_bob, room_main, BASE + timedelta(minutes=30))
            )
        assert Schedule.objects.count() == 1

    def test_create_allows_back_to_back_and_other_room(
        self, existing, instructor_bob, room_main, room_small
    ):
        create_admin_schedule(
            data=_payload(instructor_bob, room_main, BASE + timedelta(minutes=45))
        )
        create_admin_schedule(data=_payload(instructor_bob, room_small, BASE))
        assert Schedule.objects.count() == 3

    def test_create_ignores_canceled_classes(self, existing, instructor_bob, room_main):
        existing.status = constants.SCHEDULE_STATUS_CANCELED
        existing.save(update_fields=["status"])
        create_admin_schedule(data=_payload(instructor_bob, room_main, BASE))
        assert Schedule.objects.count() == 2

    def test_repeat_weeks_is_all_or_nothing(self, existing, instructor_bob, room_main):
        with pytest.raises(ValueError):
            create_admin_schedule(
                data=_payload(instructor_bob, room_main, BASE - timedelta(weeks=1), repeat_weeks=3)
            )
        assert Schedule.objects.count() == 1

    def test_update_rejects_moving_into_occupied_slot(self, existing, instructor_bob, room_main):
        other = baker.make(
            "schedules.Schedule",
            instructor=instructor_bob,
            room=room_main,
            start_time=BASE + timedelta(hours=2),
            duration_minutes=45,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        with pytest.raises(ValueError, match="La sala ya tiene una clase"):
            update_admin_schedule(schedule_id=other.id, data={"start_time": BASE})

    def test_update_of_same_class_does_not_conflict_with_itself(self, existing):
        update_admin_schedule(schedule_id=existing.id, data={"duration_minutes": 60})
        existing.refresh_from_db()
        assert existing.duration_minutes == 60

    def test_title_only_edit_does_not_block_legacy_overlaps(
        self, existing, instructor_bob, room_main
    ):
        legacy = baker.make(
            "schedules.Schedule",
            instructor=instructor_bob,
            room=room_main,
            start_time=BASE,
            duration_minutes=45,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        update_admin_schedule(schedule_id=legacy.id, data={"title": "Renamed"})
        legacy.refresh_from_db()
        assert legacy.title == "Renamed"
