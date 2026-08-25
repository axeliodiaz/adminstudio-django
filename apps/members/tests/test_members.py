import uuid
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.members import constants
from apps.members.members import (
    list_reservations_by_date_range,
    change_reservation_spot,
    create_reservation,
    cancel_reservation,
    get_member_by_id,
    get_member_by_user_id,
    get_reservation_by_id,
)
from apps.members.models import Member, Reservation
from apps.members.exceptions import (
    InvalidSpotException,
    ReservationInvalidStateException,
    RoomFullException,
)
from apps.studios.models import Address, Studio, Room
from apps.instructors.models import Instructor
from apps.schedules.models import Schedule


@pytest.mark.django_db
class TestMembersDomain:
    def test_list_reservations_by_date_range_is_inclusive_and_filters_by_dates(self, base_graph):
        member, instructor, room = base_graph

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

        start_date = base.date()
        end_date = (base + datetime.timedelta(days=1)).date()

        qs = list_reservations_by_date_range(start_date=start_date, end_date=end_date)

        assert hasattr(qs, "__iter__")  # QuerySet-like
        ids = {str(x.id) for x in qs}
        assert ids == {str(r1.id), str(r2.id)}

    def test_list_reservations_by_date_range_supports_optional_filters(self):
        User = get_user_model()
        # Two members
        u1 = User.objects.create_user(
            username=f"m1_{uuid.uuid4()}", email=f"m1_{uuid.uuid4()}@ex.com", password="pass"
        )
        u2 = User.objects.create_user(
            username=f"m2_{uuid.uuid4()}", email=f"m2_{uuid.uuid4()}@ex.com", password="pass"
        )
        m1 = Member.objects.create(user=u1)
        m2 = Member.objects.create(user=u2)
        # Studio/rooms
        address2 = Address.objects.create(address="Addr2")
        studio = Studio.objects.create(name="S2", address=address2, is_active=True)
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
        qs_member = list_reservations_by_date_range(
            start_date=start_date, end_date=end_date, member_id=str(m1.id)
        )
        assert {str(x.id) for x in qs_member} == {str(r1.id)}

        # Filter by instructor_id
        qs_instr = list_reservations_by_date_range(
            start_date=start_date, end_date=end_date, instructor_id=str(instr2.id)
        )
        assert {str(x.id) for x in qs_instr} == {str(r2.id)}

        # Filter by room_id
        qs_room = list_reservations_by_date_range(
            start_date=start_date, end_date=end_date, room_id=str(room_a.id)
        )
        assert {str(x.id) for x in qs_room} == {str(r1.id)}

    def test_list_reservations_by_date_range_filters_by_schedule_id(self, base_graph):
        member, instructor, room = base_graph

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

        # Filter by schedule_id directly (no date range needed)
        qs = list_reservations_by_date_range(schedule_id=str(s1.id))

        ids = {str(x.id) for x in qs}
        assert ids == {str(r1.id)}
        assert str(r2.id) not in ids

    def test_list_reservations_by_date_range_excludes_cancelled_reservations(self, base_graph):
        member, instructor, room = base_graph

        base = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        s_today = Schedule.objects.create(
            instructor=instructor,
            start_time=base,
            duration_minutes=60,
            room=room,
        )

        r1 = Reservation.objects.create(
            member=member, schedule=s_today, status=constants.RESERVATION_STATUS_RESERVED
        )
        r2 = Reservation.objects.create(
            member=member, schedule=s_today, status=constants.RESERVATION_STATUS_CANCELLED
        )
        r3 = Reservation.objects.create(
            member=member, schedule=s_today, status=constants.RESERVATION_STATUS_ATTENDED
        )

        start_date = base.date()
        end_date = base.date()

        qs = list_reservations_by_date_range(start_date=start_date, end_date=end_date)

        ids = {str(x.id) for x in qs}
        # Should include RESERVED and ATTENDED, but exclude CANCELLED
        assert str(r1.id) in ids
        assert str(r3.id) in ids
        assert str(r2.id) not in ids

    def test_change_reservation_spot_success_updates_spot(self):
        User = get_user_model()
        user = User.objects.create_user(
            username=f"member_{uuid.uuid4()}", email=f"m_{uuid.uuid4()}@ex.com", password="pass"
        )
        member = Member.objects.create(user=user)
        user_instructor = User.objects.create_user(
            username=f"instr_{uuid.uuid4()}", email=f"i_{uuid.uuid4()}@ex.com", password="pass"
        )
        instructor = Instructor.objects.create(user=user_instructor)
        address = Address.objects.create(address="Addr")
        studio = Studio.objects.create(name="S1", address=address, is_active=True)
        room = Room.objects.create(studio=studio, name="R1", capacity=10, is_active=True)
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            spot=1,
        )

        updated_reservation = change_reservation_spot(str(schedule.id), str(user.id), 5)

        assert updated_reservation.spot == 5
        reservation.refresh_from_db()
        assert reservation.spot == 5

    def test_change_reservation_spot_not_found_raises_exception(self):
        User = get_user_model()
        user = User.objects.create_user(
            username=f"member_{uuid.uuid4()}", email=f"m_{uuid.uuid4()}@ex.com", password="pass"
        )
        Member.objects.create(user=user)
        user_instructor = User.objects.create_user(
            username=f"instr_{uuid.uuid4()}", email=f"i_{uuid.uuid4()}@ex.com", password="pass"
        )
        instructor = Instructor.objects.create(user=user_instructor)
        address = Address.objects.create(address="Addr")
        studio = Studio.objects.create(name="S1", address=address, is_active=True)
        room = Room.objects.create(studio=studio, name="R1", capacity=10, is_active=True)
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )

        with pytest.raises(Reservation.DoesNotExist):
            change_reservation_spot(str(schedule.id), str(user.id), 5)

    def test_change_reservation_spot_invalid_state_raises_exception(self):
        User = get_user_model()
        user = User.objects.create_user(
            username=f"member_{uuid.uuid4()}", email=f"m_{uuid.uuid4()}@ex.com", password="pass"
        )
        member = Member.objects.create(user=user)
        user_instructor = User.objects.create_user(
            username=f"instr_{uuid.uuid4()}", email=f"i_{uuid.uuid4()}@ex.com", password="pass"
        )
        instructor = Instructor.objects.create(user=user_instructor)
        address = Address.objects.create(address="Addr")
        studio = Studio.objects.create(name="S1", address=address, is_active=True)
        room = Room.objects.create(studio=studio, name="R1", capacity=10, is_active=True)
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_CANCELLED,
            spot=1,
        )

        with pytest.raises(ReservationInvalidStateException):
            change_reservation_spot(str(schedule.id), str(user.id), 5)

    def test_change_reservation_spot_invalid_spot_range_raises_exception(self):
        User = get_user_model()
        user = User.objects.create_user(
            username=f"member_{uuid.uuid4()}", email=f"m_{uuid.uuid4()}@ex.com", password="pass"
        )
        member = Member.objects.create(user=user)
        user_instructor = User.objects.create_user(
            username=f"instr_{uuid.uuid4()}", email=f"i_{uuid.uuid4()}@ex.com", password="pass"
        )
        instructor = Instructor.objects.create(user=user_instructor)
        address = Address.objects.create(address="Addr")
        studio = Studio.objects.create(name="S1", address=address, is_active=True)
        room = Room.objects.create(studio=studio, name="R1", capacity=10, is_active=True)
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            spot=1,
        )

        # Test spot < 1
        with pytest.raises(InvalidSpotException):
            change_reservation_spot(str(schedule.id), str(user.id), 0)

        # Test spot > capacity
        with pytest.raises(InvalidSpotException):
            change_reservation_spot(str(schedule.id), str(user.id), 11)

    def test_change_reservation_spot_spot_already_taken_raises_exception(self):
        User = get_user_model()
        user1 = User.objects.create_user(
            username=f"member1_{uuid.uuid4()}", email=f"m1_{uuid.uuid4()}@ex.com", password="pass"
        )
        user2 = User.objects.create_user(
            username=f"member2_{uuid.uuid4()}", email=f"m2_{uuid.uuid4()}@ex.com", password="pass"
        )
        member1 = Member.objects.create(user=user1)
        member2 = Member.objects.create(user=user2)
        user_instructor = User.objects.create_user(
            username=f"instr_{uuid.uuid4()}", email=f"i_{uuid.uuid4()}@ex.com", password="pass"
        )
        instructor = Instructor.objects.create(user=user_instructor)
        address = Address.objects.create(address="Addr")
        studio = Studio.objects.create(name="S1", address=address, is_active=True)
        room = Room.objects.create(studio=studio, name="R1", capacity=10, is_active=True)
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        Reservation.objects.create(
            member=member1,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            spot=1,
        )
        Reservation.objects.create(
            member=member2,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            spot=5,
        )

        # Try to change member1's spot to 5, which is already taken by member2
        with pytest.raises(InvalidSpotException):
            change_reservation_spot(str(schedule.id), str(user1.id), 5)

    def test_create_reservation_success_creates_reservation(self, mocker, base_graph):
        mocker.patch("apps.members.notifications.send_reservation_confirmed_email")
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )

        validated_data = {
            "user_id": member.user.id,
            "schedule_id": schedule.id,
            "spot": 1,
            "notes": "Test notes",
        }

        reservation = create_reservation(validated_data)

        assert reservation.member == member
        assert reservation.schedule == schedule
        assert reservation.spot == 1
        assert reservation.notes == "Test notes"
        assert reservation.status == constants.RESERVATION_STATUS_RESERVED

    def test_create_reservation_sends_confirmed_email(self, mocker, base_graph):
        send_email = mocker.patch("apps.members.notifications.send_reservation_confirmed_email")
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            title="Power Ride 45",
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )

        reservation = create_reservation(
            {
                "user_id": member.user.id,
                "schedule_id": schedule.id,
                "spot": 3,
            }
        )

        send_email.assert_called_once_with(reservation)

    def test_create_reservation_creates_member_if_not_exists(self, mocker, base_graph):
        _, instructor, room = base_graph
        # Mock create_verification_code to avoid Celery connection issues
        mocker.patch("apps.members.members.create_verification_code")
        mocker.patch("apps.members.notifications.send_reservation_confirmed_email")
        User = get_user_model()
        user = User.objects.create_user(
            username=f"newuser_{uuid.uuid4()}",
            email=f"newuser_{uuid.uuid4()}@ex.com",
            password="pass",
        )
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )

        validated_data = {
            "user_id": user.id,
            "schedule_id": schedule.id,
            "spot": 1,
        }

        reservation = create_reservation(validated_data)

        # Member should be created
        member = Member.objects.get(user=user)
        assert reservation.member == member

    def test_create_reservation_invalid_spot_less_than_one_raises_exception(self, base_graph):
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )

        validated_data = {
            "user_id": member.user.id,
            "schedule_id": schedule.id,
            "spot": 0,
        }

        with pytest.raises(InvalidSpotException):
            create_reservation(validated_data)

    def test_create_reservation_invalid_spot_greater_than_capacity_raises_exception(
        self, base_graph
    ):
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )

        validated_data = {
            "user_id": member.user.id,
            "schedule_id": schedule.id,
            "spot": room.capacity + 1,
        }

        with pytest.raises(InvalidSpotException):
            create_reservation(validated_data)

    def test_cancel_reservation_success_cancels_reservation(self, base_graph):
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            spot=1,
        )

        cancelled_reservation = cancel_reservation(str(reservation.id))

        assert cancelled_reservation.status == constants.RESERVATION_STATUS_CANCELLED
        reservation.refresh_from_db()
        assert reservation.status == constants.RESERVATION_STATUS_CANCELLED

    def test_cancel_reservation_within_free_window_raises(self, base_graph):
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(minutes=30),
            duration_minutes=45,
            room=room,
        )
        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            spot=1,
        )

        with pytest.raises(ReservationInvalidStateException):
            cancel_reservation(str(reservation.id))

    def test_cancel_reservation_bypass_free_window_for_staff(self, base_graph):
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(minutes=30),
            duration_minutes=45,
            room=room,
        )
        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
            spot=1,
        )

        cancelled = cancel_reservation(str(reservation.id), bypass_free_cancel_window=True)
        assert cancelled.status == constants.RESERVATION_STATUS_CANCELLED

    def test_cancel_reservation_not_found_raises_exception(self):
        with pytest.raises(Reservation.DoesNotExist):
            cancel_reservation(str(uuid.uuid4()))

    def test_cancel_reservation_invalid_state_raises_exception(self, base_graph):
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_CANCELLED,
            spot=1,
        )

        with pytest.raises(ReservationInvalidStateException):
            cancel_reservation(str(reservation.id))

    def test_get_member_by_id_success(self, base_graph):
        member, _, _ = base_graph
        found_member = get_member_by_id(str(member.id))
        assert found_member == member

    def test_get_member_by_id_not_found_raises_exception(self):
        with pytest.raises(Member.DoesNotExist):
            get_member_by_id(str(uuid.uuid4()))

    def test_get_member_by_user_id_success(self, base_graph):
        member, _, _ = base_graph
        found_member = get_member_by_user_id(str(member.user.id))
        assert found_member == member

    def test_get_member_by_user_id_not_found_raises_exception(self):
        User = get_user_model()
        user = User.objects.create_user(
            username=f"nouser_{uuid.uuid4()}",
            email=f"nouser_{uuid.uuid4()}@ex.com",
            password="pass",
        )
        with pytest.raises(Member.DoesNotExist):
            get_member_by_user_id(str(user.id))

    def test_get_reservation_by_id_success(self, base_graph):
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            spot=1,
        )

        found_reservation = get_reservation_by_id(str(reservation.id))
        assert found_reservation == reservation

    def test_get_reservation_by_id_not_found_raises_exception(self):
        with pytest.raises(Reservation.DoesNotExist):
            get_reservation_by_id(str(uuid.uuid4()))

    def test_public_member_register_creates_inactive_user_with_password(self, mocker):
        from apps.members.members import get_or_create_member_user

        verify_mock = mocker.patch("apps.members.members.create_verification_code")
        password = "S3cretPass!"
        member, created = get_or_create_member_user(
            {
                "email": "rider@example.com",
                "password": password,
                "first_name": "Ana",
                "last_name": "Rider",
                "phone_number": "+56911111111",
            },
            is_active=False,
        )

        user = member.user
        assert created is True
        assert user.is_active is False
        assert user.check_password(password)
        verify_mock.assert_called_once_with(user=user)
