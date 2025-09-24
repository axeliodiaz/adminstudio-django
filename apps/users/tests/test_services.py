"""Tests for users services module, mirroring notifications tests structure."""

import pytest

from apps.users.services import create_user, get_user_from_id


class TestCreateUser:
    @pytest.mark.django_db
    def test_create_user_invokes_django_create_user_and_ignores_input_password(
        self, mocker, validated_registration_data
    ):
        # Arrange
        validated = validated_registration_data
        token_mock = mocker.patch(
            "apps.users.services.secrets.token_urlsafe", return_value="RANDOM_PASS"
        )

        create_user_manager_mock = mocker.patch(
            "apps.users.services.User.objects.create_user",
        )
        # Returned user instance from manager: no 'phone' attribute so hasattr(..., 'phone') is False
        returned_user = mocker.Mock(spec=["save"])  # provide save but no 'phone'
        create_user_manager_mock.return_value = returned_user

        # Act
        result = create_user(validated)

        # Assert
        token_mock.assert_called_once()
        create_user_manager_mock.assert_called_once_with(
            username=validated["email"],
            password="RANDOM_PASS",
            email=validated["email"],
            first_name=validated["first_name"],
            last_name=validated["last_name"],
        )
        # Since the model has phone_number, not 'phone', the service should not try to save
        assert not getattr(returned_user, "save").called
        assert result is returned_user


class TestGetUserFromId:
    def test_fetches_user_and_serializes_with_schema(self, mocker, serialized_user_payload):
        # Arrange
        fake_user = mocker.Mock()
        get_obj_mock = mocker.patch("apps.users.services.get_object_or_404", return_value=fake_user)

        schema_instance = mocker.Mock()
        schema_instance.model_dump.return_value = serialized_user_payload
        model_validate_mock = mocker.patch(
            "apps.users.services.UserSchema.model_validate", return_value=schema_instance
        )

        # Act
        payload = get_user_from_id("some-id")

        # Assert
        from apps.users.services import User

        get_obj_mock.assert_called_once_with(User, id="some-id")
        model_validate_mock.assert_called_once_with(fake_user)
        assert payload == schema_instance.model_dump.return_value
