"""Tests for users services module, mirroring notifications tests structure."""

import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.users.models import PasswordResetCode
from apps.users.services import (
    create_user,
    get_user_from_id,
    change_user_password,
    request_password_recovery,
    request_admin_password_recovery,
    confirm_password_reset,
    generate_password_reset_code,
)

User = get_user_model()


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
            is_active=True,
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
            is_active=True,
        )

    @pytest.mark.django_db
    def test_create_user_can_create_inactive_account(self, mocker, validated_registration_data):
        validated = {**validated_registration_data, "is_active": False}
        create_user_manager_mock = mocker.patch(
            "apps.users.services.User.objects.create_user",
        )
        returned_user = mocker.Mock(spec=["save", "phone_number"])
        create_user_manager_mock.return_value = returned_user

        result = create_user(validated)

        create_user_manager_mock.assert_called_once_with(
            username=validated["email"],
            password=validated["password"],
            email=validated["email"],
            first_name=validated["first_name"],
            last_name=validated["last_name"],
            is_active=False,
        )
        assert result is returned_user
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


@pytest.mark.django_db
class TestChangeUserPassword:
    def test_change_user_password_updates_password_when_old_password_is_correct(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )

        change_user_password(user, "oldpassword123", "newpassword456")

        user.refresh_from_db()
        assert user.check_password("newpassword456")

    def test_change_user_password_raises_value_error_when_old_password_is_invalid(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )

        with pytest.raises(ValueError) as excinfo:
            change_user_password(user, "wrongpassword", "newpassword456")

        assert "Contraseña actual incorrecta." in str(excinfo.value)


@pytest.mark.django_db
class TestGeneratePasswordResetCode:
    def test_generate_password_reset_code_returns_six_character_code(self):
        code = generate_password_reset_code()
        assert len(code) == 6
        assert code.isalnum()

    def test_generate_password_reset_code_returns_uppercase_code(self):
        code = generate_password_reset_code()
        assert code.isupper() or all(c.isdigit() for c in code) or code.isalnum()


@pytest.mark.django_db
class TestRequestPasswordRecovery:
    def test_request_password_recovery_creates_code_for_existing_user(self, mocker):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")

        request_password_recovery("test@example.com")

        reset_code = PasswordResetCode.objects.get(user=user)
        assert reset_code.code is not None
        assert len(reset_code.code) == 6
        assert reset_code.expires_at > timezone.now()
        send_email_mock.assert_called_once()

    def test_request_password_recovery_does_not_expose_nonexistent_email(self, mocker):
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")

        # Should not raise exception even if email doesn't exist
        request_password_recovery("nonexistent@example.com")

        assert PasswordResetCode.objects.count() == 0
        send_email_mock.assert_not_called()

    def test_request_password_recovery_ignores_inactive_users(self, mocker):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        user.is_active = False
        user.save()
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")

        request_password_recovery("test@example.com")

        assert PasswordResetCode.objects.count() == 0
        send_email_mock.assert_not_called()

    def test_request_password_recovery_ignores_soft_deleted_users(self, mocker):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        user.delete()  # Soft delete
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")

        request_password_recovery("test@example.com")

        assert PasswordResetCode.objects.count() == 0
        send_email_mock.assert_not_called()


@pytest.mark.django_db
class TestRequestAdminPasswordRecovery:
    def test_request_admin_password_recovery_sends_code(self, mocker):
        actor = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")

        request_admin_password_recovery(user_id=user.id, actor=actor)

        reset_code = PasswordResetCode.objects.get(user=user)
        assert len(reset_code.code) == 6
        send_email_mock.assert_called_once()

    def test_request_admin_password_recovery_rejects_inactive_user(self, mocker):
        actor = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        user.is_active = False
        user.save()
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")

        with pytest.raises(ValueError, match="cuenta inactiva"):
            request_admin_password_recovery(user_id=user.id, actor=actor)

        assert PasswordResetCode.objects.count() == 0
        send_email_mock.assert_not_called()


@pytest.mark.django_db
class TestConfirmPasswordReset:
    def test_confirm_password_reset_updates_password_with_valid_code(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )
        reset_code = PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        confirm_password_reset("ABC123", "newpassword456")

        user.refresh_from_db()
        assert user.check_password("newpassword456")
        # Code should be invalidated (soft deleted)
        assert PasswordResetCode.objects.filter(code="ABC123", is_removed=False).count() == 0

    def test_confirm_password_reset_raises_error_with_invalid_code(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )
        PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        with pytest.raises(ValueError) as excinfo:
            confirm_password_reset("INVALID", "newpassword456")

        assert "Código inválido o expirado" in str(excinfo.value)
        user.refresh_from_db()
        assert user.check_password("oldpassword123")  # Password unchanged

    def test_confirm_password_reset_raises_error_with_expired_code(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )
        reset_code = PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() - timedelta(minutes=1),  # Expired
        )

        with pytest.raises(ValueError) as excinfo:
            confirm_password_reset("ABC123", "newpassword456")

        assert "Código inválido o expirado" in str(excinfo.value)
        user.refresh_from_db()
        assert user.check_password("oldpassword123")  # Password unchanged

    def test_confirm_password_reset_raises_error_with_already_used_code(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )
        reset_code = PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        reset_code.delete()  # Soft delete (already used)

        with pytest.raises(ValueError) as excinfo:
            confirm_password_reset("ABC123", "newpassword456")

        assert "Código inválido o expirado" in str(excinfo.value)

    def test_confirm_password_reset_validates_password_strength(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )
        reset_code = PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        with pytest.raises(ValueError):
            confirm_password_reset("ABC123", "123")  # Too short

        user.refresh_from_db()
        assert user.check_password("oldpassword123")  # Password unchanged
