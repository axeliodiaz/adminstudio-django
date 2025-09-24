"""Tests for riders services module."""

import pytest

from apps.riders.services import get_or_create_rider_user, get_or_create_user


class TestGetOrCreateUser:
    @pytest.mark.django_db
    def test_returns_existing_user_without_creating(self, mocker, existing_user):
        # Arrange: existing user with given email
        create_user_mock = mocker.patch("apps.riders.services.create_user")

        # Act
        returned = get_or_create_user({"email": existing_user.email})

        # Assert
        assert returned == existing_user
        create_user_mock.assert_not_called()

    @pytest.mark.django_db
    def test_creates_user_when_missing(self, mocker, new_user_data):
        # Arrange: no user with this email exists
        mocked_user = mocker.Mock()
        create_user_mock = mocker.patch(
            "apps.riders.services.create_user", return_value=mocked_user
        )

        # Act
        returned = get_or_create_user(new_user_data)

        # Assert
        create_user_mock.assert_called_once_with(new_user_data)
        assert returned is mocked_user


class TestGetOrCreateRiderUser:
    @pytest.mark.django_db
    def test_returns_existing_rider_and_does_not_trigger_verification(
        self, mocker, existing_rider, rider_user
    ):
        # Arrange: create user and rider via fixtures
        verification_mock = mocker.patch("apps.riders.services.create_verification_code")

        # Act
        result_rider, created = get_or_create_rider_user({"email": rider_user.email})

        # Assert: no new rider, created flag false, no verification sent
        assert result_rider == existing_rider
        assert created is False
        verification_mock.assert_not_called()

    @pytest.mark.django_db
    def test_creates_rider_when_missing_and_triggers_verification(self, mocker, user_without_rider):
        # Arrange: user exists, but rider does not
        verification_mock = mocker.patch("apps.riders.services.create_verification_code")

        # Act
        rider, created = get_or_create_rider_user({"email": user_without_rider.email})

        # Assert
        assert created is True
        assert rider.user == user_without_rider
        verification_mock.assert_called_once_with(user=rider.user)
