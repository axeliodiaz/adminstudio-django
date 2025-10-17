import uuid
import pytest

from apps.members import constants
from apps.members.models import Reservation, Member
from apps.members.exceptions import ReservationInvalidStateException
from apps.members.services import cancel_reservation as service_cancel_reservation

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
