import uuid
import datetime
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.members import constants
from apps.members.models import Member, Reservation
from apps.members.members import get_reservation_by_id, cancel_reservation
from apps.members.exceptions import ReservationInvalidStateException
from apps.studios.models import Studio, Room
from apps.instructors.models import Instructor
from apps.schedules.models import Schedule


@pytest.mark.django_db
class TestMembersDomain:
    def _build_graph(self):
        # Create user and related member and instructor
        User = get_user_model()
        user_member = User.objects.create_user(
            username=f"member_{uuid.uuid4()}", email=f"m_{uuid.uuid4()}@ex.com", password="pass"
        )
        user_instructor = User.objects.create_user(
            username=f"instr_{uuid.uuid4()}", email=f"i_{uuid.uuid4()}@ex.com", password="pass"
        )
        member = Member.objects.create(user=user_member)
        instructor = Instructor.objects.create(user=user_instructor)

        # Create studio, room, and schedule
        studio = Studio.objects.create(name="S1", address="Addr", is_active=True)
        room = Room.objects.create(studio=studio, name="R1", capacity=10, is_active=True)
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        return member, schedule

    def test_get_reservation_by_id_success(self):
        member, schedule = self._build_graph()
        reservation = Reservation.objects.create(member=member, schedule=schedule, notes="")

        fetched = get_reservation_by_id(str(reservation.id))
        assert fetched.id == reservation.id

    def test_get_reservation_by_id_not_found(self):
        with pytest.raises(Reservation.DoesNotExist):
            get_reservation_by_id(str(uuid.uuid4()))

    def test_cancel_reservation_success(self):
        member, schedule = self._build_graph()
        reservation = Reservation.objects.create(
            member=member, schedule=schedule, status=constants.RESERVATION_STATUS_RESERVED
        )

        updated = cancel_reservation(str(reservation.id))
        assert updated.status == constants.RESERVATION_STATUS_CANCELLED
        # Re-fetch to ensure persisted
        db_obj = Reservation.objects.get(id=reservation.id)
        assert db_obj.status == constants.RESERVATION_STATUS_CANCELLED

    def test_cancel_reservation_raises_on_invalid_state(self):
        member, schedule = self._build_graph()
        reservation = Reservation.objects.create(
            member=member, schedule=schedule, status=constants.RESERVATION_STATUS_CANCELLED
        )

        with pytest.raises(ReservationInvalidStateException) as exc:
            cancel_reservation(str(reservation.id))
        assert "Only RESERVED reservations can be cancelled" in str(exc.value)

    def test_cancel_reservation_not_found(self):
        with pytest.raises(Reservation.DoesNotExist):
            cancel_reservation(str(uuid.uuid4()))
