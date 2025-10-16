"""Tests for members services module."""

from apps.members.services import (
    get_or_create_member_user,
    get_or_create_user,
    get_member_from_user_id,
)

import pytest
from model_bakery import baker

from apps.members.models import Reservation, Member
from apps.members.services import create_reservation


@pytest.mark.django_db
class TestCreateReservationService:
    def test_creates_reservation_and_returns_schema_for_existing_member(self, existing_member):
        schedule = baker.make("schedules.Schedule")

        schema = create_reservation(
            {
                "user_id": existing_member.user.id,
                "schedule_id": schedule.id,
            }
        )

        # Validate schema fields
        assert schema.member_id == existing_member.id
        assert schema.schedule_id == schedule.id
        assert schema.status == "RESERVED"

        # Ensure persisted in DB
        assert Reservation.objects.filter(member=existing_member, schedule=schedule).count() == 1


class TestGetOrCreateUser:
    @pytest.mark.django_db
    def test_returns_existing_user_without_creating(self, mocker, existing_user):
        # Arrange: existing user with given email
        create_user_mock = mocker.patch("apps.users.services.create_user")

        # Act
        returned = get_or_create_user({"email": existing_user.email})

        # Assert
        assert returned == existing_user
        create_user_mock.assert_not_called()

    @pytest.mark.django_db
    def test_creates_user_when_missing(self, mocker, new_user_data):
        # Arrange: no user with this email exists
        mocked_user = mocker.Mock()
        create_user_mock = mocker.patch("apps.users.services.create_user", return_value=mocked_user)

        # Act
        returned = get_or_create_user(new_user_data)

        # Assert
        create_user_mock.assert_called_once_with(new_user_data)
        assert returned is mocked_user


class TestGetOrCreateMemberUser:
    @pytest.mark.django_db
    def test_returns_existing_member_and_does_not_trigger_verification(
        self, mocker, existing_member, member_user
    ):
        # Arrange: create user and member via fixtures
        verification_mock = mocker.patch("apps.members.members.create_verification_code")

        # Act
        member_schema, created = get_or_create_member_user({"email": member_user.email})

        # Assert: no new member, created flag false, no verification sent
        assert created is False
        assert member_schema.user.email == member_user.email
        verification_mock.assert_not_called()

    @pytest.mark.django_db
    def test_creates_member_when_missing_and_triggers_verification(
        self, mocker, user_without_member
    ):
        # Arrange: user exists, but member does not
        verification_mock = mocker.patch("apps.members.members.create_verification_code")

        # Act
        member_schema, created = get_or_create_member_user({"email": user_without_member.email})

        # Assert
        assert created is True
        assert member_schema.user.email == user_without_member.email
        verification_mock.assert_called_once()


class TestGetMemberFromUserIdService:
    @pytest.mark.django_db
    def test_returns_member_schema_when_exists(self, existing_member):
        schema = get_member_from_user_id(existing_member.user.id)
        assert schema.id == existing_member.id
        assert schema.user.email == existing_member.user.email

    @pytest.mark.django_db
    def test_raises_does_not_exist_for_unknown_user_id(self):
        import uuid

        with pytest.raises(Member.DoesNotExist):
            get_member_from_user_id(uuid.uuid4())
