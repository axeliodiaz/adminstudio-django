from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from drf_expiring_token.models import ExpiringToken

from apps.members.alerts import (
    DAILY_ALERT_LIMIT,
    notify_favorite_spot_available,
    notify_schedule_available,
)
from apps.members.members import cancel_reservation, create_reservation
from apps.members.models import (
    AlertDelivery,
    AlertPreference,
    FavoriteInstructor,
    FavoriteSpot,
    WaitlistEntry,
)
from apps.members import constants as member_constants
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule


@pytest.mark.django_db
def test_favorites_and_preferences_replace_document(base_graph):
    member, instructor, room = base_graph
    client = APIClient()
    token = ExpiringToken.objects.create(user=member.user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.put(
        "/api/profiles/favorites/",
        {
            "instructor_ids": [str(instructor.id)],
            "time_slots": [{"weekday": 0, "start_hour": 8, "end_hour": 10}],
            "spots": [{"room_id": str(room.id), "spot": 2}],
        },
        format="json",
    )
    assert response.status_code == 200
    assert len(response.data["instructor_ids"]) == 1
    assert (
        client.put(
            "/api/alerts/preferences/",
            {"email_enabled": False, "quiet_hours_start": 22, "quiet_hours_end": 7},
            format="json",
        ).status_code
        == 200
    )
    preference = AlertPreference.objects.get(member=member)
    assert not preference.email_enabled


@pytest.mark.django_db
def test_schedule_alert_dedupes_and_respects_daily_limit(base_graph, mocker):
    member, instructor, room = base_graph
    FavoriteInstructor.objects.create(member=member, instructor=instructor)
    send = mocker.patch("apps.notifications.services.create_notification")
    schedule = Schedule.objects.create(
        instructor=instructor,
        room=room,
        start_time=timezone.now() + timedelta(days=1),
        duration_minutes=45,
        status=schedule_constants.SCHEDULE_STATUS_SCHEDULED,
    )
    notify_schedule_available(schedule)
    notify_schedule_available(schedule)
    assert send.call_count == 1
    for index in range(DAILY_ALERT_LIMIT - 1):
        AlertDelivery.objects.create(member=member, event_key=f"old:{index}", kind="SCHEDULE")
    second = Schedule.objects.create(
        instructor=instructor,
        room=room,
        start_time=timezone.now() + timedelta(days=2),
        duration_minutes=45,
        status=schedule_constants.SCHEDULE_STATUS_SCHEDULED,
    )
    notify_schedule_available(second)
    assert send.call_count == 1


@pytest.mark.django_db
def test_spot_alert_skips_waitlisted_member_and_prioritizes_waitlist(base_graph, mocker):
    member, instructor, room = base_graph
    FavoriteSpot.objects.create(member=member, room=room, spot=3)
    schedule = Schedule.objects.create(
        instructor=instructor,
        room=room,
        start_time=timezone.now() + timedelta(days=1),
        duration_minutes=45,
        status=schedule_constants.SCHEDULE_STATUS_SCHEDULED,
    )
    WaitlistEntry.objects.create(
        member=member, schedule=schedule, status=member_constants.WAITLIST_STATUS_WAITING
    )
    send = mocker.patch("apps.notifications.services.create_notification")
    notify_favorite_spot_available(schedule, 3)
    assert not send.called
    assert not AlertDelivery.objects.exists()


@pytest.mark.django_db
def test_cancel_reservation_triggers_free_spot_alert(base_graph, mocker):
    member, instructor, room = base_graph
    from django.contrib.auth import get_user_model
    from apps.members.models import Member

    favorite_user = get_user_model().objects.create_user(
        username="favorite-alert-member", email="favorite-alert@example.com", password="pass"
    )
    favorite_member = Member.objects.create(user=favorite_user)
    FavoriteSpot.objects.create(member=favorite_member, room=room, spot=4)
    schedule = Schedule.objects.create(
        instructor=instructor,
        room=room,
        start_time=timezone.now() + timedelta(days=2),
        duration_minutes=45,
        status=schedule_constants.SCHEDULE_STATUS_SCHEDULED,
    )
    reservation = create_reservation(
        {"user_id": member.user_id, "schedule_id": schedule.id, "spot": 4}
    )
    send = mocker.patch("apps.notifications.services.create_notification")
    cancel_reservation(str(reservation.id))
    assert send.call_count == 1
    assert AlertDelivery.objects.filter(member=favorite_member, kind="SPOT").exists()


@pytest.mark.django_db
def test_public_schedule_query_hides_non_scheduled_classes(base_graph):
    _, instructor, room = base_graph
    scheduled = Schedule.objects.create(
        instructor=instructor,
        room=room,
        start_time=timezone.now() + timedelta(days=1),
        duration_minutes=45,
        status=schedule_constants.SCHEDULE_STATUS_SCHEDULED,
    )
    Schedule.objects.create(
        instructor=instructor,
        room=room,
        start_time=timezone.now() + timedelta(days=2),
        duration_minutes=45,
        status=schedule_constants.SCHEDULE_STATUS_DRAFT,
    )
    response = APIClient().get("/api/schedules/")
    assert response.status_code == 200
    assert [str(row["id"]) for row in response.data] == [str(scheduled.id)]
