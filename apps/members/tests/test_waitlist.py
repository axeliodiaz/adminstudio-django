import datetime
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.members import constants
from apps.members.exceptions import WaitlistException
from apps.members.models import Member, Reservation, WaitlistEntry
from apps.members.waitlist import confirm_waitlist_offer, join_waitlist, leave_waitlist
from apps.schedules.models import Schedule

User = get_user_model()


def _make_member(suffix=""):
    user = User.objects.create_user(
        username=f"wl_{suffix}_{uuid.uuid4()}",
        email=f"wl_{suffix}_{uuid.uuid4()}@ex.com",
        password="pass",
        first_name="Wait",
        last_name=suffix or "List",
    )
    return Member.objects.create(user=user)


def _fill_schedule(schedule, count):
    members = []
    for i in range(count):
        member = _make_member(f"fill{i}")
        Reservation.objects.create(
            member=member,
            schedule=schedule,
            spot=i + 1,
            status=constants.RESERVATION_STATUS_RESERVED,
        )
        members.append(member)
    return members


@pytest.mark.django_db
class TestWaitlistDomain:
    def test_join_waitlist_when_class_is_full(self, base_graph, mocker):
        mocker.patch("apps.notifications.services.create_notification")
        member, instructor, room = base_graph
        room.capacity = 1
        room.save(update_fields=["capacity"])
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
            title="HIIT Ride",
        )
        _fill_schedule(schedule, 1)
        waiter = _make_member("join")

        entry = join_waitlist(user_id=waiter.user_id, schedule_id=schedule.id)

        assert entry.status == constants.WAITLIST_STATUS_WAITING
        assert WaitlistEntry.objects.filter(member=waiter, schedule=schedule).count() == 1

    def test_join_waitlist_rejects_when_class_has_capacity(self, base_graph):
        member, instructor, room = base_graph
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        with pytest.raises(WaitlistException, match="aún tiene cupos"):
            join_waitlist(user_id=member.user_id, schedule_id=schedule.id)

    def test_cancel_reservation_offers_spot_to_first_in_line(self, base_graph, mocker):
        notify = mocker.patch("apps.notifications.services.create_notification")
        _, instructor, room = base_graph
        room.capacity = 1
        room.save(update_fields=["capacity"])
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
            title="Power Ride",
        )
        holders = _fill_schedule(schedule, 1)
        waiter = _make_member("first")
        join_waitlist(user_id=waiter.user_id, schedule_id=schedule.id)

        from apps.members.members import cancel_reservation

        cancel_reservation(str(Reservation.objects.get(member=holders[0]).id))

        entry = WaitlistEntry.objects.get(member=waiter, schedule=schedule)
        assert entry.status == constants.WAITLIST_STATUS_OFFERED
        assert entry.offered_spot == 1
        notify.assert_called_once()

    def test_auto_confirm_converts_waitlist_on_cancel(self, base_graph, mocker):
        mocker.patch("apps.notifications.services.create_notification")
        _, instructor, room = base_graph
        room.capacity = 1
        room.save(update_fields=["capacity"])
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        holders = _fill_schedule(schedule, 1)
        waiter = _make_member("auto")
        waiter.user.waitlist_auto_confirm = True
        waiter.user.save(update_fields=["waitlist_auto_confirm"])
        join_waitlist(user_id=waiter.user_id, schedule_id=schedule.id)

        from apps.members.members import cancel_reservation

        cancel_reservation(str(Reservation.objects.get(member=holders[0]).id))

        entry = WaitlistEntry.objects.get(member=waiter)
        assert entry.status == constants.WAITLIST_STATUS_CONVERTED
        assert Reservation.objects.filter(
            member=waiter, status=constants.RESERVATION_STATUS_RESERVED, spot=1
        ).exists()

    def test_confirm_offer_creates_reservation(self, base_graph, mocker):
        mocker.patch("apps.notifications.services.create_notification")
        _, instructor, room = base_graph
        room.capacity = 1
        room.save(update_fields=["capacity"])
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        holders = _fill_schedule(schedule, 1)
        waiter = _make_member("confirm")
        join_waitlist(user_id=waiter.user_id, schedule_id=schedule.id)
        from apps.members.members import cancel_reservation

        cancel_reservation(str(Reservation.objects.get(member=holders[0]).id))
        entry = WaitlistEntry.objects.get(member=waiter)

        confirmed = confirm_waitlist_offer(user_id=waiter.user_id, waitlist_id=entry.id)

        assert confirmed.status == constants.WAITLIST_STATUS_CONVERTED
        assert Reservation.objects.filter(member=waiter, spot=1).exists()

    def test_leave_waitlist_marks_left(self, base_graph):
        _, instructor, room = base_graph
        room.capacity = 1
        room.save(update_fields=["capacity"])
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        _fill_schedule(schedule, 1)
        waiter = _make_member("leave")
        entry = join_waitlist(user_id=waiter.user_id, schedule_id=schedule.id)

        left = leave_waitlist(user_id=waiter.user_id, waitlist_id=entry.id)

        assert left.status == constants.WAITLIST_STATUS_LEFT


@pytest.mark.django_db
class TestWaitlistViews:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    def _auth(self, api_client, member):
        api_client.force_authenticate(user=member.user)
        return api_client

    def test_join_and_list_waitlist(self, api_client, base_graph, mocker):
        mocker.patch("apps.notifications.services.create_notification")
        _, instructor, room = base_graph
        room.capacity = 1
        room.save(update_fields=["capacity"])
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
            title="Friday Sprint",
        )
        _fill_schedule(schedule, 1)
        waiter = _make_member("api")
        self._auth(api_client, waiter)

        resp = api_client.post(
            reverse("waitlist"), {"schedule_id": str(schedule.id)}, format="json"
        )
        assert resp.status_code == 201
        assert resp.data["position"] == 1
        assert resp.data["schedule"]["title"] == "Friday Sprint"

        listed = api_client.get(reverse("waitlist"))
        assert listed.status_code == 200
        assert len(listed.data) == 1
        assert listed.data[0]["id"] == resp.data["id"]

    def test_leave_waitlist(self, api_client, base_graph):
        _, instructor, room = base_graph
        room.capacity = 1
        room.save(update_fields=["capacity"])
        schedule = Schedule.objects.create(
            instructor=instructor,
            start_time=timezone.now() + datetime.timedelta(days=1),
            duration_minutes=45,
            room=room,
        )
        _fill_schedule(schedule, 1)
        waiter = _make_member("apileave")
        self._auth(api_client, waiter)
        created = api_client.post(
            reverse("waitlist"), {"schedule_id": str(schedule.id)}, format="json"
        )
        resp = api_client.delete(reverse("waitlist-detail", args=[created.data["id"]]))
        assert resp.status_code == 200
        assert (
            WaitlistEntry.objects.get(id=created.data["id"]).status
            == constants.WAITLIST_STATUS_LEFT
        )
