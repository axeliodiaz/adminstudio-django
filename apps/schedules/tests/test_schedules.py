import pytest
from datetime import datetime, timezone, timedelta

from apps.schedules.schedules import get_schedules_list
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from apps.schedules import constants
from apps.schedules.models import Schedule
from apps.schedules.schedules import create_schedule


class TestGetSchedulesList:
    @pytest.mark.django_db
    def test_returns_all_ordered_by_start_time(self, schedules_sample):
        qs = get_schedules_list()
        times = list(qs.values_list("start_time", flat=True))
        assert times == sorted(times)
        assert qs.count() == 3

    @pytest.mark.django_db
    def test_filters_by_start_time_gte(self, schedules_sample):
        # Use middle time threshold to include last two
        threshold = schedules_sample[0].start_time + timedelta(minutes=30)
        qs = get_schedules_list(start_time=threshold)
        ids = list(qs.values_list("id", flat=True))
        assert set(ids) == {schedules_sample[1].id, schedules_sample[2].id}

    @pytest.mark.django_db
    def test_filters_by_instructor_username_icontains(self, schedules_sample):
        qs = get_schedules_list(instructor_username="ali")  # matches 'alice'
        ids = set(qs.values_list("id", flat=True))
        assert ids == {schedules_sample[0].id, schedules_sample[1].id}

    @pytest.mark.django_db
    def test_filters_by_room_name_icontains(self, schedules_sample):
        qs = get_schedules_list(room_name="main")
        ids = set(qs.values_list("id", flat=True))
        assert ids == {schedules_sample[0].id, schedules_sample[2].id}

    @pytest.mark.django_db
    def test_combined_filters(self, schedules_sample):
        threshold = schedules_sample[0].start_time + timedelta(minutes=30)
        qs = get_schedules_list(start_time=threshold, instructor_username="ali", room_name="small")
        ids = list(qs.values_list("id", flat=True))
        assert ids == [schedules_sample[1].id]


class TestCreateSchedule:
    @pytest.mark.django_db
    def test_create_schedule_success(self, instructor_alice, room_main):
        start = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
        sched = create_schedule(
            instructor_id=instructor_alice.id,
            start_time=start,
            duration_minutes=45,
            room_id=room_main.id,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        assert isinstance(sched, Schedule)
        # persisted
        assert Schedule.objects.filter(id=sched.id).exists()
        # field assertions
        assert sched.instructor_id == instructor_alice.id
        assert sched.room_id == room_main.id
        assert sched.start_time == start
        assert sched.duration_minutes == 45
        assert sched.status == constants.SCHEDULE_STATUS_SCHEDULED

    @pytest.mark.django_db
    def test_invalid_status_raises_value_error(self, instructor_alice, room_main):
        with pytest.raises(ValueError, match="Invalid schedule status"):
            create_schedule(
                instructor_id=instructor_alice.id,
                start_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
                duration_minutes=30,
                room_id=room_main.id,
                status="not-a-valid-status",
            )

    @pytest.mark.django_db
    @pytest.mark.parametrize("duration", [0, -5])
    def test_non_positive_duration_raises_value_error(self, duration, instructor_alice, room_main):
        with pytest.raises(ValueError, match="duration_minutes must be a positive integer"):
            create_schedule(
                instructor_id=instructor_alice.id,
                start_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
                duration_minutes=duration,
                room_id=room_main.id,
                status=constants.SCHEDULE_STATUS_DRAFT,
            )

    @pytest.mark.django_db
    def test_nonexistent_instructor_raises_object_does_not_exist(self, room_main):
        with pytest.raises(ObjectDoesNotExist):
            create_schedule(
                instructor_id=uuid.uuid4(),
                start_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
                duration_minutes=30,
                room_id=room_main.id,
                status=constants.SCHEDULE_STATUS_DRAFT,
            )

    @pytest.mark.django_db
    def test_nonexistent_room_raises_http404(self, instructor_alice):
        with pytest.raises(Http404):
            create_schedule(
                instructor_id=instructor_alice.id,
                start_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
                duration_minutes=30,
                room_id=uuid.uuid4(),
                status=constants.SCHEDULE_STATUS_DRAFT,
            )
