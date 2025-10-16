"""Tests for users services module, mirroring notifications tests structure."""

import pytest

from apps.users.services import create_user, get_user_from_id


class TestCreateUser:
    @pytest.mark.django_db
    def test_create_user_uses_provided_password_when_present(
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
        # Returned user instance from manager: has phone_number attr per model, but our service will set it via save
        returned_user = mocker.Mock(spec=["save", "phone_number"])  # provide save and phone_number
        create_user_manager_mock.return_value = returned_user

        # Act
        result = create_user(validated)

        # Assert
        # Provided password should be used; no random password generation
        token_mock.assert_not_called()
        create_user_manager_mock.assert_called_once_with(
            username=validated["email"],
            password=validated["password"],
            email=validated["email"],
            first_name=validated["first_name"],
            last_name=validated["last_name"],
        )
        # phone_number should be saved via update_fields when attribute exists
        assert getattr(returned_user, "save").called
        assert result is returned_user

    @pytest.mark.django_db
    def test_create_user_generates_random_password_when_missing(
        self, mocker, validated_registration_data
    ):
        # Arrange: remove password to force generation
        validated = {k: v for k, v in validated_registration_data.items() if k != "password"}
        token_mock = mocker.patch(
            "apps.users.services.secrets.token_urlsafe", return_value="RANDOM_PASS"
        )
        create_user_manager_mock = mocker.patch(
            "apps.users.services.User.objects.create_user",
        )
        returned_user = mocker.Mock(spec=["save", "phone_number"])
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
        assert getattr(returned_user, "save").called
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
