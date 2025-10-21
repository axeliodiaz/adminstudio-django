import uuid
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.members.members import list_reservations_by_date_range
from apps.members.models import Member, Reservation
from apps.studios.models import Studio, Room
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
        studio = Studio.objects.create(name="S2", address="Addr2", is_active=True)
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
