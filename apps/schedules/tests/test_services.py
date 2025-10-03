import pytest
from datetime import datetime, timedelta, timezone

from apps.schedules.services import (
    get_schedule_schema_list,
    create_schedule,
    to_schedule_schema_list,
)
from apps.schedules import constants
from apps.schedules.models import Schedule


class TestServicesGetScheduleSchemaList:
    @pytest.mark.django_db
    def test_returns_all_as_schemas_ordered(self, schedules_sample):
        schemas = get_schedule_schema_list()
        assert len(schemas) == 3
        # Ensure sorted by start_time
        times = [s.start_time for s in schemas]
        assert times == sorted(times)
        # Ensure items are pydantic models exposing id
        assert {s.id for s in schemas} == {s.id for s in schedules_sample}

    @pytest.mark.django_db
    def test_filters_by_start_time(self, schedules_sample):
        threshold = schedules_sample[0].start_time + timedelta(minutes=30)
        schemas = get_schedule_schema_list(start_time=threshold)
        ids = {s.id for s in schemas}
        assert ids == {schedules_sample[1].id, schedules_sample[2].id}

    @pytest.mark.django_db
    def test_filters_by_instructor_username(self, schedules_sample):
        schemas = get_schedule_schema_list(instructor_username="ali")
        ids = {s.id for s in schemas}
        assert ids == {schedules_sample[0].id, schedules_sample[1].id}

    @pytest.mark.django_db
    def test_filters_by_room_name(self, schedules_sample):
        schemas = get_schedule_schema_list(room_name="main")
        ids = {s.id for s in schemas}
        assert ids == {schedules_sample[0].id, schedules_sample[2].id}

    @pytest.mark.django_db
    def test_combined_filters(self, schedules_sample):
        threshold = schedules_sample[0].start_time + timedelta(minutes=30)
        schemas = get_schedule_schema_list(
            start_time=threshold, instructor_username="ali", room_name="small"
        )
        ids = [s.id for s in schemas]
        assert ids == [schedules_sample[1].id]


class TestServicesCreateSchedule:
    @pytest.mark.django_db
    def test_create_schedule_success_returns_schema_and_persists(self, instructor_alice, room_main):
        start = datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)
        schema = create_schedule(
            instructor_id=instructor_alice.id,
            start_time=start,
            duration_minutes=50,
            room_id=room_main.id,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        # Returned is a pydantic schema with expected fields
        assert schema.id is not None
        assert schema.instructor_id == instructor_alice.id
        assert schema.room_id == room_main.id
        assert schema.duration_minutes == 50
        assert schema.status == constants.SCHEDULE_STATUS_SCHEDULED
        assert schema.start_time == start
        # Ensure object exists in DB
        obj = Schedule.objects.get(id=schema.id)
        assert obj.instructor_id == instructor_alice.id
        assert obj.room_id == room_main.id

    @pytest.mark.django_db
    def test_create_schedule_invalid_status_raises(self, instructor_alice, room_main):
        with pytest.raises(ValueError):
            create_schedule(
                instructor_id=instructor_alice.id,
                start_time=datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc),
                duration_minutes=45,
                room_id=room_main.id,
                status="invalid-status",
            )

    @pytest.mark.django_db
    def test_create_schedule_non_positive_duration_raises(self, instructor_alice, room_main):
        with pytest.raises(ValueError):
            create_schedule(
                instructor_id=instructor_alice.id,
                start_time=datetime(2025, 1, 2, 11, 0, tzinfo=timezone.utc),
                duration_minutes=0,
                room_id=room_main.id,
                status=constants.SCHEDULE_STATUS_DRAFT,
            )


class TestServicesToScheduleSchemaList:
    @pytest.mark.django_db
    def test_converts_list_of_models(self, schedules_sample):
        schemas = to_schedule_schema_list(schedules_sample)
        assert len(schemas) == 3
        assert {s.id for s in schemas} == {obj.id for obj in schedules_sample}

    @pytest.mark.django_db
    def test_converts_queryset(self, schedules_sample):
        qs = Schedule.objects.all()
        schemas = to_schedule_schema_list(qs)
        assert len(schemas) == 3
        assert {s.id for s in schemas} == set(qs.values_list("id", flat=True))
