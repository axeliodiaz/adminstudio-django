"""Tests for members services module."""

import pytest

from apps.members.services import get_or_create_member_user, get_or_create_user


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
        verification_mock = mocker.patch("apps.members.services.create_verification_code")

        # Act
        result_member, created = get_or_create_member_user({"email": member_user.email})

        # Assert: no new member, created flag false, no verification sent
        assert result_member == existing_member
        assert created is False
        verification_mock.assert_not_called()

    @pytest.mark.django_db
    def test_creates_member_when_missing_and_triggers_verification(
        self, mocker, user_without_member
    ):
        # Arrange: user exists, but member does not
        verification_mock = mocker.patch("apps.members.services.create_verification_code")

        # Act
        member, created = get_or_create_member_user({"email": user_without_member.email})

        # Assert
        assert created is True
        assert member.user == user_without_member
        verification_mock.assert_called_once_with(user=member.user)
