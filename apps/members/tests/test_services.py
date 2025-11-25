import uuid
import pytest

from apps.members import constants
from apps.members.models import Reservation, Member
from apps.members.exceptions import ReservationInvalidStateException, InvalidSpotException
from apps.members.services import (
    cancel_reservation as service_cancel_reservation,
    list_reservations as service_list_reservations,
    change_reservation_spot as service_change_reservation_spot,
)

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.studios.models import Studio, Room
from apps.instructors.models import Instructor
from apps.schedules.models import Schedule
import datetime


@pytest.mark.django_db
class TestMembersServices:
    def _build_graph(self):
        User = get_user_model()
        user_member = User.objects.create_user(
            username=f"member_{uuid.uuid4()}", email=f"m_{uuid.uuid4()}@ex.com", password="pass"
        )
        user_instructor = User.objects.create_user(
            username=f"instr_{uuid.uuid4()}", email=f"i_{uuid.uuid4()}@ex.com", password="pass"
        )
        member = Member.objects.create(user=user_member)
        instructor = Instructor.objects.create(user=user_instructor)
        studio = Studio.objects.create(name="S1", address="Addr", is_active=True)
        room = Room.objects.create(studio=studio, name="R1", capacity=10, is_active=True)
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        return member, schedule

    def test_cancel_reservation_success_returns_schema_and_updates_db(self):
        member, schedule = self._build_graph()
        reservation = Reservation.objects.create(
            member=member, schedule=schedule, status=constants.RESERVATION_STATUS_RESERVED
        )

        schema = service_cancel_reservation(str(reservation.id))

        # Returned object is a Pydantic ReservationSchema-like with attributes
        assert str(schema.id) == str(reservation.id)
        assert schema.status == constants.RESERVATION_STATUS_CANCELLED

        # DB is updated
        reservation.refresh_from_db()
        assert reservation.status == constants.RESERVATION_STATUS_CANCELLED

    def test_cancel_reservation_not_found_bubbles_up(self):
        with pytest.raises(Reservation.DoesNotExist):
            service_cancel_reservation(str(uuid.uuid4()))

    def test_cancel_reservation_invalid_state_bubbles_custom_exception(self):
        member, schedule = self._build_graph()
        reservation = Reservation.objects.create(
            member=member, schedule=schedule, status=constants.RESERVATION_STATUS_CANCELLED
        )

        with pytest.raises(ReservationInvalidStateException):
            service_cancel_reservation(str(reservation.id))

    def test_list_reservations_filters_by_date_range_and_returns_schemas(self):
        # Setup base entities
        User = get_user_model()
        user_member = User.objects.create_user(
            username=f"member_{uuid.uuid4()}", email=f"m_{uuid.uuid4()}@ex.com", password="pass"
        )
        member = Member.objects.create(user=user_member)
        studio = Studio.objects.create(name="S2", address="Addr2", is_active=True)
        room = Room.objects.create(studio=studio, name="R2", capacity=10, is_active=True)
        instructor_user = User.objects.create_user(
            username=f"instr_{uuid.uuid4()}", email=f"i2_{uuid.uuid4()}@ex.com", password="pass"
        )
        instructor = Instructor.objects.create(user=instructor_user)

        base = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        s_today = Schedule.objects.create(
            instructor=instructor,
            start_time=base,
            duration_minutes=60,
            room=room,
        )
        s_tomorrow = Schedule.objects.create(
            instructor=instructor,
            start_time=base + datetime.timedelta(days=1),
            duration_minutes=60,
            room=room,
        )
        s_future = Schedule.objects.create(
            instructor=instructor,
            start_time=base + datetime.timedelta(days=3),
            duration_minutes=60,
            room=room,
        )

        r1 = Reservation.objects.create(member=member, schedule=s_today)
        r2 = Reservation.objects.create(member=member, schedule=s_tomorrow)
        Reservation.objects.create(member=member, schedule=s_future)

        # Date range inclusive: today..tomorrow should include r1 and r2, exclude future
        start_date = base.date()
        end_date = (base + datetime.timedelta(days=1)).date()
        result = service_list_reservations({"start_date": start_date, "end_date": end_date})

        assert isinstance(result, list)
        ids = {str(obj.id) for obj in result}
        assert ids == {str(r1.id), str(r2.id)}
        # Ensure returned items have expected attributes (Pydantic model)
        for obj in result:
            assert hasattr(obj, "member_id")
            assert hasattr(obj, "schedule_id")
            assert hasattr(obj, "status")

    def test_list_reservations_supports_optional_filters(self):
        User = get_user_model()
        # Members
        u1 = User.objects.create_user(
            username=f"m1_{uuid.uuid4()}", email=f"m1_{uuid.uuid4()}@ex.com", password="pass"
        )
        u2 = User.objects.create_user(
            username=f"m2_{uuid.uuid4()}", email=f"m2_{uuid.uuid4()}@ex.com", password="pass"
        )
        m1 = Member.objects.create(user=u1)
        m2 = Member.objects.create(user=u2)
        # Studio/rooms
        studio = Studio.objects.create(name="S3", address="Addr3", is_active=True)
        room_a = Room.objects.create(studio=studio, name="RA", capacity=10, is_active=True)
        room_b = Room.objects.create(studio=studio, name="RB", capacity=10, is_active=True)
        # Instructors
        iu1 = User.objects.create_user(
            username=f"i1_{uuid.uuid4()}", email=f"i1_{uuid.uuid4()}@ex.com", password="pass"
        )
        iu2 = User.objects.create_user(
            username=f"i2_{uuid.uuid4()}", email=f"i2_{uuid.uuid4()}@ex.com", password="pass"
        )
        instr1 = Instructor.objects.create(user=iu1)
        instr2 = Instructor.objects.create(user=iu2)

        base = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        same_day = base
        s1 = Schedule.objects.create(
            instructor=instr1, start_time=same_day, duration_minutes=45, room=room_a
        )
        s2 = Schedule.objects.create(
            instructor=instr2, start_time=same_day, duration_minutes=45, room=room_b
        )

        r1 = Reservation.objects.create(member=m1, schedule=s1)
        r2 = Reservation.objects.create(member=m2, schedule=s2)

        start_date = same_day.date()
        end_date = same_day.date()

        # Filter by member_id
        res_member = service_list_reservations(
            {
                "start_date": start_date,
                "end_date": end_date,
                "member_id": str(m1.id),
            }
        )
        assert {str(x.id) for x in res_member} == {str(r1.id)}

        # Filter by instructor_id
        res_instr = service_list_reservations(
            {
                "start_date": start_date,
                "end_date": end_date,
                "schedule__instructor_id": str(instr2.id),
            }
        )
        assert {str(x.id) for x in res_instr} == {str(r2.id)}

        # Filter by room_id
        res_room = service_list_reservations(
            {
                "start_date": start_date,
                "end_date": end_date,
                "schedule__room_id": str(room_a.id),
            }
        )
        assert {str(x.id) for x in res_room} == {str(r1.id)}

    def test_list_reservations_filters_by_schedule_id(self):
        User = get_user_model()
        user_member = User.objects.create_user(
            username=f"member_{uuid.uuid4()}", email=f"m_{uuid.uuid4()}@ex.com", password="pass"
        )
        member = Member.objects.create(user=user_member)
        studio = Studio.objects.create(name="S4", address="Addr4", is_active=True)
        room = Room.objects.create(studio=studio, name="R4", capacity=10, is_active=True)
        instructor_user = User.objects.create_user(
            username=f"instr_{uuid.uuid4()}", email=f"i4_{uuid.uuid4()}@ex.com", password="pass"
        )
        instructor = Instructor.objects.create(user=instructor_user)

        base = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        s1 = Schedule.objects.create(
            instructor=instructor,
            start_time=base,
            duration_minutes=60,
            room=room,
        )
        s2 = Schedule.objects.create(
            instructor=instructor,
            start_time=base + datetime.timedelta(days=1),
            duration_minutes=60,
            room=room,
        )

        r1 = Reservation.objects.create(member=member, schedule=s1)
        r2 = Reservation.objects.create(member=member, schedule=s2)

        # Filter by schedule_id - should only return reservations for s1
        result = service_list_reservations({"schedule_id": str(s1.id)})

        assert isinstance(result, list)
        ids = {str(obj.id) for obj in result}
        assert ids == {str(r1.id)}
        assert str(result[0].schedule_id) == str(s1.id)

    def test_change_reservation_spot_success_returns_schema_and_updates_db(self):
        member, schedule = self._build_graph()
        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            spot=1,
        )

        schema = service_change_reservation_spot(str(schedule.id), str(member.user.id), 5)

        # Returned object is a Pydantic ReservationSchema-like with attributes
        assert str(schema.id) == str(reservation.id)
        assert schema.spot == 5

        # DB is updated
        reservation.refresh_from_db()
        assert reservation.spot == 5

    def test_change_reservation_spot_not_found_bubbles_up(self):
        member, schedule = self._build_graph()
        with pytest.raises(Reservation.DoesNotExist):
            service_change_reservation_spot(str(schedule.id), str(member.user.id), 5)

    def test_change_reservation_spot_invalid_state_bubbles_custom_exception(self):
        member, schedule = self._build_graph()
        Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_CANCELLED,
            spot=1,
        )

        with pytest.raises(ReservationInvalidStateException):
            service_change_reservation_spot(str(schedule.id), str(member.user.id), 5)

    def test_change_reservation_spot_invalid_spot_bubbles_exception(self):
        member, schedule = self._build_graph()
        Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            spot=1,
        )

        # Test spot out of range
        with pytest.raises(InvalidSpotException):
            service_change_reservation_spot(str(schedule.id), str(member.user.id), 11)
