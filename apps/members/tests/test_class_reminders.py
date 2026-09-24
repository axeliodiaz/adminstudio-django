from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.members import constants as member_constants
from apps.members.models import Reservation
from apps.notifications.models import Notification
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule


def _make_schedule(instructor, room, *, start_time, status=schedule_constants.SCHEDULE_STATUS_SCHEDULED, title="RIDE 45"):
    return Schedule.objects.create(
        title=title,
        instructor=instructor,
        room=room,
        status=status,
        start_time=start_time,
    )


@pytest.mark.django_db
def test_reminder_goes_out_the_day_before(base_graph):
    member, instructor, room = base_graph
    tomorrow = timezone.localdate() + timedelta(days=1)
    start = timezone.make_aware(
        timezone.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 7, 0)
    )
    schedule = _make_schedule(instructor, room, start_time=start)
    reservation = Reservation.objects.create(
        member=member,
        schedule=schedule,
        status=member_constants.RESERVATION_STATUS_RESERVED,
        spot=18,
    )

    call_command("send_class_reminders")

    reservation.refresh_from_db()
    assert reservation.reminder_sent_at is not None
    notification = Notification.objects.get(user=member.user)
    assert "RIDE 45" in notification.subject
    assert "7:00" in notification.subject
    assert "Spot 18" in notification.html_content
    assert "toalla" in notification.html_content


@pytest.mark.django_db
def test_command_is_idempotent(base_graph):
    member, instructor, room = base_graph
    tomorrow = timezone.localdate() + timedelta(days=1)
    start = timezone.make_aware(
        timezone.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 19, 0)
    )
    schedule = _make_schedule(instructor, room, start_time=start)
    Reservation.objects.create(
        member=member,
        schedule=schedule,
        status=member_constants.RESERVATION_STATUS_RESERVED,
    )

    call_command("send_class_reminders")
    call_command("send_class_reminders")

    assert Notification.objects.filter(user=member.user).count() == 1


@pytest.mark.django_db
def test_other_days_and_states_are_skipped(base_graph):
    member, instructor, room = base_graph
    today = timezone.localdate()
    start_today = timezone.make_aware(
        timezone.datetime(today.year, today.month, today.day, 23, 30)
    )
    today_schedule = _make_schedule(instructor, room, start_time=start_today)
    Reservation.objects.create(
        member=member,
        schedule=today_schedule,
        status=member_constants.RESERVATION_STATUS_RESERVED,
    )

    tomorrow = today + timedelta(days=1)
    start_tomorrow = timezone.make_aware(
        timezone.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 8, 0)
    )
    cancelled_schedule = _make_schedule(
        instructor,
        room,
        start_time=start_tomorrow,
        status=schedule_constants.SCHEDULE_STATUS_CANCELED,
    )
    Reservation.objects.create(
        member=member,
        schedule=cancelled_schedule,
        status=member_constants.RESERVATION_STATUS_RESERVED,
    )
    member_reservation_cancelled = Reservation.objects.create(
        member=member,
        schedule=_make_schedule(instructor, room, start_time=start_tomorrow, title="YOGA 45"),
        status=member_constants.RESERVATION_STATUS_CANCELLED,
    )

    call_command("send_class_reminders")

    assert Notification.objects.filter(user=member.user).count() == 0
    member_reservation_cancelled.refresh_from_db()
    assert member_reservation_cancelled.reminder_sent_at is None
