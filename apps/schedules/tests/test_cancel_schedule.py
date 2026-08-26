"""Tests for studio class cancellation cascade (refund + notify + waitlist expire)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.members import constants as member_constants
from apps.members.models import Member, Reservation, WaitlistEntry
from apps.members.notifications import send_class_cancelled_email
from apps.schedules import constants
from apps.schedules.models import Schedule
from apps.schedules.services import cancel_admin_schedule, update_admin_schedule
from apps.wallets.models import Wallet

User = get_user_model()


@pytest.mark.django_db
class TestCancelAdminSchedule:
    def test_cancel_cascades_reservations_refunds_and_emails(self, mocker, base_graph):
        send_email = mocker.patch(
            "apps.members.notifications.send_class_cancelled_email",
            wraps=send_class_cancelled_email,
        )
        create_notification = mocker.patch("apps.members.notifications.create_notification")
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            title="Morning Climb",
            start_time=timezone.now() + timedelta(days=2),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        wallet = Wallet.objects.get(user=member.user)
        wallet.class_credits = 5
        wallet.save(update_fields=["class_credits"])

        reservation = Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=member_constants.RESERVATION_STATUS_RESERVED,
            spot=1,
            credit_charged=True,
        )
        other_user = User.objects.create_user(
            username="wait2", email="wait2@ex.com", password="pass"
        )
        other_member = Member.objects.create(user=other_user)
        WaitlistEntry.objects.create(
            member=other_member,
            schedule=schedule,
            status=member_constants.WAITLIST_STATUS_WAITING,
        )

        result = cancel_admin_schedule(schedule_id=schedule.id, reason="instructor no disponible")

        schedule.refresh_from_db()
        reservation.refresh_from_db()
        wallet.refresh_from_db()

        assert result["status"] == constants.SCHEDULE_STATUS_CANCELED
        assert result["cancellation_reason"] == "instructor no disponible"
        assert schedule.status == constants.SCHEDULE_STATUS_CANCELED
        assert reservation.status == member_constants.RESERVATION_STATUS_CANCELLED
        assert reservation.cancellation_source == member_constants.CANCELLATION_SOURCE_SCHEDULE
        assert reservation.credit_charged is False
        assert wallet.class_credits == 6
        send_email.assert_called_once()
        create_notification.assert_called_once()
        html = create_notification.call_args.kwargs["html_content"]
        assert "Tuvimos que cancelar la clase" in html
        assert "instructor no disponible" in html
        assert (
            WaitlistEntry.objects.filter(
                schedule=schedule, status=member_constants.WAITLIST_STATUS_WAITING
            ).count()
            == 0
        )
        assert WaitlistEntry.objects.filter(
            schedule=schedule, status=member_constants.WAITLIST_STATUS_EXPIRED
        ).exists()

    def test_update_status_to_canceled_triggers_cascade(self, mocker, base_graph):
        mocker.patch("apps.members.notifications.send_class_cancelled_email")
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            title="Power",
            start_time=timezone.now() + timedelta(days=1),
            duration_minutes=45,
            room=room,
            status=constants.SCHEDULE_STATUS_SCHEDULED,
        )
        Reservation.objects.create(
            member=member,
            schedule=schedule,
            status=member_constants.RESERVATION_STATUS_RESERVED,
            spot=2,
            credit_charged=True,
        )

        update_admin_schedule(
            schedule_id=schedule.id,
            data={
                "status": constants.SCHEDULE_STATUS_CANCELED,
                "cancellation_reason": "mantención sala",
            },
        )

        schedule.refresh_from_db()
        assert schedule.status == constants.SCHEDULE_STATUS_CANCELED
        assert schedule.cancellation_reason == "mantención sala"
        assert Reservation.objects.filter(
            schedule=schedule,
            status=member_constants.RESERVATION_STATUS_CANCELLED,
            cancellation_source=member_constants.CANCELLATION_SOURCE_SCHEDULE,
        ).exists()
