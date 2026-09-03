"""Substitute coach: overlap checks, audit history, rider emails, reservation integrity."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.members import constants as member_constants
from apps.members.models import Member, Reservation, WaitlistEntry
from apps.members.notifications import send_coach_substituted_email
from apps.schedules import constants
from apps.schedules.models import Schedule, ScheduleInstructorSubstitution
from apps.schedules.services import substitute_coach

User = get_user_model()


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="subadmin",
        email="subadmin@example.com",
        password="pass1234",
        is_staff=True,
        first_name="Ops",
        last_name="Admin",
    )


@pytest.fixture
def staff_client(api_client, staff_user):
    token = ExpiringToken.objects.create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


def _make_instructor(suffix="bob"):
    user = User.objects.create_user(
        username=f"instr_{suffix}",
        email=f"{suffix}@ex.com",
        password="pass",
        first_name=suffix.title(),
        last_name="Coach",
        is_active=True,
    )
    from apps.instructors.models import Instructor

    return Instructor.objects.create(user=user)


@pytest.mark.django_db
class TestSubstituteCoachService:
    def test_replaces_instructor_keeps_reservation_and_emails(self, mocker, base_graph, staff_user):
        send_email = mocker.patch(
            "apps.members.notifications.send_coach_substituted_email",
            wraps=send_coach_substituted_email,
        )
        create_notification = mocker.patch("apps.members.notifications.create_notification")
        member, instructor, room = base_graph
        substitute = _make_instructor("camila")
        schedule = Schedule.objects.create(
            instructor=instructor,
            title="Morning Climb",
            start_time=timezone.now() + timedelta(days=2),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=member_constants.RESERVATION_STATUS_RESERVED,
            spot=7,
            credit_charged=True,
        )
        wait_user = User.objects.create_user(
            username="wait_sub", email="wait_sub@ex.com", password="pass"
        )
        wait_member = Member.objects.create(user=wait_user)
        WaitlistEntry.objects.create(
            member=wait_member,
            schedule=schedule,
            status=member_constants.WAITLIST_STATUS_WAITING,
        )

        result = substitute_coach(
            schedule_id=schedule.id,
            new_instructor_id=substitute.id,
            reason="lesión",
            notify=True,
            changed_by=staff_user,
        )

        schedule.refresh_from_db()
        reservation.refresh_from_db()
        assert schedule.instructor_id == substitute.id
        assert reservation.spot == 7
        assert reservation.status == member_constants.RESERVATION_STATUS_RESERVED
        assert result["instructor_id"] == str(substitute.id)
        assert result["reservation_count"] == 1
        assert result["waitlist_count"] == 1
        history = ScheduleInstructorSubstitution.objects.get(schedule=schedule)
        assert history.old_instructor_id == instructor.id
        assert history.new_instructor_id == substitute.id
        assert history.changed_by_id == staff_user.id
        assert history.reason == "lesión"
        assert history.reserved_notified == 1
        assert history.waitlist_notified == 1
        assert send_email.call_count == 2
        audiences = {call.kwargs["audience"] for call in send_email.call_args_list}
        assert audiences == {"reservation", "waitlist"}
        assert create_notification.call_count == 2
        html = create_notification.call_args_list[0].kwargs["html_content"]
        assert "Cambio de coach" in html
        assert "lesión" in html

    def test_waitlist_only_still_notifies(self, mocker, base_graph, staff_user):
        mocker.patch("apps.members.notifications.send_coach_substituted_email")
        member, instructor, room = base_graph
        substitute = _make_instructor("diego")
        schedule = Schedule.objects.create(
            instructor=instructor,
            title="Power",
            start_time=timezone.now() + timedelta(hours=3),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        WaitlistEntry.objects.create(
            member=member,
            schedule=schedule,
            status=member_constants.WAITLIST_STATUS_WAITING,
        )

        result = substitute_coach(
            schedule_id=schedule.id,
            new_instructor_id=substitute.id,
            notify=True,
            changed_by=staff_user,
        )
        assert result["reservation_count"] == 0
        assert result["waitlist_count"] == 1
        history = ScheduleInstructorSubstitution.objects.get(schedule=schedule)
        assert history.reserved_notified == 0
        assert history.waitlist_notified == 1

    def test_blocks_overlap(self, base_graph):
        member, instructor, room = base_graph
        substitute = _make_instructor("eva")
        start = timezone.now() + timedelta(days=1)
        Schedule.objects.create(
            instructor=substitute,
            title="Other",
            start_time=start + timedelta(minutes=15),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        target = Schedule.objects.create(
            instructor=instructor,
            title="Target",
            start_time=start,
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        with pytest.raises(ValueError, match="mismo horario"):
            substitute_coach(schedule_id=target.id, new_instructor_id=substitute.id)

        target.refresh_from_db()
        assert target.instructor_id == instructor.id
        assert not ScheduleInstructorSubstitution.objects.exists()

    def test_blocks_canceled_and_inactive_and_same_coach(self, base_graph):
        _, instructor, room = base_graph
        substitute = _make_instructor("fran")
        canceled = Schedule.objects.create(
            instructor=instructor,
            title="X",
            start_time=timezone.now() + timedelta(days=1),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_CANCELED,
        )
        with pytest.raises(ValueError, match="cancelada"):
            substitute_coach(schedule_id=canceled.id, new_instructor_id=substitute.id)

        live = Schedule.objects.create(
            instructor=instructor,
            title="Y",
            start_time=timezone.now() + timedelta(days=2),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        with pytest.raises(ValueError, match="distinto"):
            substitute_coach(schedule_id=live.id, new_instructor_id=instructor.id)

        substitute.user.is_active = False
        substitute.user.save(update_fields=["is_active"])
        with pytest.raises(ValueError, match="no está activo"):
            substitute_coach(schedule_id=live.id, new_instructor_id=substitute.id)

    def test_notify_false_skips_email(self, mocker, base_graph, staff_user):
        send_email = mocker.patch("apps.members.notifications.send_coach_substituted_email")
        member, instructor, room = base_graph
        substitute = _make_instructor("gina")
        schedule = Schedule.objects.create(
            instructor=instructor,
            title="Quiet",
            start_time=timezone.now() + timedelta(days=1),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=member_constants.RESERVATION_STATUS_RESERVED,
            spot=1,
        )
        substitute_coach(
            schedule_id=schedule.id,
            new_instructor_id=substitute.id,
            notify=False,
            changed_by=staff_user,
        )
        send_email.assert_not_called()
        history = ScheduleInstructorSubstitution.objects.get(schedule=schedule)
        assert history.notify is False
        assert history.reserved_notified == 0


@pytest.mark.django_db
class TestSubstituteCoachViews:
    def test_requires_staff(self, api_client, base_graph):
        _, instructor, room = base_graph
        substitute = _make_instructor("hugo")
        schedule = Schedule.objects.create(
            instructor=instructor,
            title="Staff only",
            start_time=timezone.now() + timedelta(days=1),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        user = User.objects.create_user(username="member", email="m@ex.com", password="pass1234")
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.post(
            reverse("admin-schedule-substitute-coach", kwargs={"schedule_id": schedule.id}),
            data={"new_instructor_id": str(substitute.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_preview_and_assign_via_admin_url(self, staff_client, base_graph, mocker):
        mocker.patch("apps.members.notifications.send_coach_substituted_email")
        _, instructor, room = base_graph
        substitute = _make_instructor("iris")
        schedule = Schedule.objects.create(
            instructor=instructor,
            title="Ride",
            start_time=timezone.now() + timedelta(days=1),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        preview = staff_client.get(
            reverse("admin-schedule-substitute-coach", kwargs={"schedule_id": schedule.id}),
            {"instructor_id": str(substitute.id)},
        )
        assert preview.status_code == status.HTTP_200_OK
        assert preview.data["candidate"]["eligible"] is True
        assert preview.data["reservation_count"] == 0

        assigned = staff_client.post(
            reverse("admin-schedule-substitute-coach", kwargs={"schedule_id": schedule.id}),
            data={
                "new_instructor_id": str(substitute.id),
                "reason": "viaje",
                "notify": True,
            },
            format="json",
        )
        assert assigned.status_code == status.HTTP_200_OK
        assert assigned.data["instructor_id"] == str(substitute.id)
        assert assigned.data["substitution"]["reason"] == "viaje"
        assert assigned.data["substitutions"]

    def test_public_path_is_staff_only_and_works(self, staff_client, base_graph, mocker):
        mocker.patch("apps.members.notifications.send_coach_substituted_email")
        _, instructor, room = base_graph
        substitute = _make_instructor("jules")
        schedule = Schedule.objects.create(
            instructor=instructor,
            title="Ride",
            start_time=timezone.now() + timedelta(days=1),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        response = staff_client.post(
            reverse("schedule-substitute-coach", kwargs={"pk": schedule.id}),
            data={"new_instructor_id": str(substitute.id), "notify": False},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["instructor_id"] == str(substitute.id)
