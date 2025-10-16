"""Domain-layer tests for apps.members.members module."""

import uuid

import pytest
from model_bakery import baker

from apps.members.members import create_reservation, get_or_create_member_user
from apps.members.models import Member, Reservation


@pytest.mark.django_db
class TestGetOrCreateMemberUserDomain:
    def test_returns_existing_member_without_verification(
        self, mocker, existing_member, member_user
    ):
        # Ensure preconditions
        assert Member.objects.filter(user=member_user).exists()
        verification_mock = mocker.patch("apps.members.members.create_verification_code")

        member, created = get_or_create_member_user({"email": member_user.email})

        assert created is False
        assert isinstance(member, Member)
        assert member.user == member_user
        verification_mock.assert_not_called()

    def test_creates_member_and_triggers_verification(self, mocker, user_without_member):
        assert not Member.objects.filter(user=user_without_member).exists()
        verification_mock = mocker.patch("apps.members.members.create_verification_code")

        member, created = get_or_create_member_user({"email": user_without_member.email})

        assert created is True
        assert isinstance(member, Member)
        assert member.user == user_without_member
        verification_mock.assert_called_once()


@pytest.mark.django_db
class TestCreateReservationDomain:
    def test_creates_reservation_for_existing_member(self, existing_member):
        schedule = baker.make("schedules.Schedule")

        reservation = create_reservation(
            {
                "user_id": existing_member.user.id,
                "schedule_id": schedule.id,
            }
        )

        assert isinstance(reservation, Reservation)
        assert reservation.member_id == existing_member.id
        assert reservation.schedule_id == schedule.id
        assert reservation.status == "RESERVED"
        assert reservation.notes == ""  # default notes when not provided
        # ensure persisted
        assert Reservation.objects.filter(id=reservation.id).exists()

    def test_accepts_optional_notes_and_persists(self, existing_member):
        schedule = baker.make("schedules.Schedule")
        notes = "Prefer front row"

        reservation = create_reservation(
            {
                "user_id": existing_member.user.id,
                "schedule_id": schedule.id,
                "notes": notes,
            }
        )

        assert reservation.notes == notes

    def test_creates_member_if_missing_then_reservation(self, mocker, member_missing_email):
        # No user or member with this email; create user and member first
        # Create a user with the missing email so domain creates member for it via users service
        user = baker.make("users.User", email=member_missing_email)
        schedule = baker.make("schedules.Schedule")
        # Avoid hitting external broker via notifications by mocking verification side-effect
        verification_mock = mocker.patch("apps.members.members.create_verification_code")

        reservation = create_reservation(
            {
                "user_id": user.id,
                "schedule_id": schedule.id,
            }
        )

        # The member should now exist and be linked
        member = Member.objects.get(user=user)
        assert reservation.member_id == member.id
        assert reservation.schedule_id == schedule.id
        verification_mock.assert_called_once()


class TestGetMemberByIdDomain:
    @pytest.mark.django_db
    def test_returns_member_when_exists(self, existing_member):
        from apps.members.members import get_member_by_id

        fetched = get_member_by_id(existing_member.id)
        assert isinstance(fetched, Member)
        assert fetched.id == existing_member.id

    @pytest.mark.django_db
    def test_raises_does_not_exist_for_unknown_id(self):
        from apps.members.members import get_member_by_id
        import uuid

        with pytest.raises(Member.DoesNotExist):
            get_member_by_id(uuid.uuid4())


@pytest.mark.django_db
class TestGetScheduledReservationsByMemberAndSchedule:
    def test_returns_only_reserved_for_member_and_schedule(self):
        from apps.members.members import (
            get_scheduled_reservations_by_member_id_and_schedule_id as get_qs,
        )
        from apps.members import constants

        member = baker.make("members.Member")
        schedule = baker.make("schedules.Schedule")
        # Should be included (RESERVED by same member in same schedule)
        r_included = baker.make(
            "members.Reservation",
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
        )
        # Exclusions
        baker.make(
            "members.Reservation",
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_CANCELLED,
        )
        baker.make(
            "members.Reservation",
            member=member,
            schedule=baker.make("schedules.Schedule"),
            status=constants.RESERVATION_STATUS_RESERVED,
        )
        baker.make(
            "members.Reservation",
            member=baker.make("members.Member"),
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
        )

        qs = get_qs(member.id, schedule.id)
        ids = set(qs.values_list("id", flat=True))
        assert ids == {r_included.id}

    def test_returns_empty_when_no_reservations(self):
        from apps.members.members import (
            get_scheduled_reservations_by_member_id_and_schedule_id as get_qs,
        )

        member = baker.make("members.Member")
        schedule = baker.make("schedules.Schedule")

        qs = get_qs(member.id, schedule.id)
        assert qs.count() == 0

    def test_accepts_uuid_and_str_ids(self):
        from apps.members.members import (
            get_scheduled_reservations_by_member_id_and_schedule_id as get_qs,
        )
        from apps.members import constants

        member = baker.make("members.Member")
        schedule = baker.make("schedules.Schedule")
        r = baker.make(
            "members.Reservation",
            member=member,
            schedule=schedule,
            status=constants.RESERVATION_STATUS_RESERVED,
        )

        # UUID inputs
        qs_uuid = get_qs(member.id, schedule.id)
        assert set(qs_uuid.values_list("id", flat=True)) == {r.id}

        # String inputs
        qs_str = get_qs(str(member.id), str(schedule.id))
        assert set(qs_str.values_list("id", flat=True)) == {r.id}
