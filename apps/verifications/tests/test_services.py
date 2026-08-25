"""Tests for verifications services module."""

import re
import uuid

import pytest
from django.conf import settings
from model_bakery import baker

from apps.verifications import constants
from apps.verifications.services import (
    create_verification_code,
    generate_verification_code,
    send_email_verification,
    validate_code,
)


class TestValidateCode:
    @pytest.mark.django_db
    def test_activates_user_and_soft_deletes_code(self, mocker, inactive_user, verification_code):
        # Precondition
        assert not inactive_user.is_active
        assert not verification_code.is_removed

        welcome_mock = mocker.patch("apps.verifications.services.send_welcome_email")

        # Act
        returned = validate_code(verification_code)

        # Assert: user is activated and code soft-deleted
        inactive_user.refresh_from_db()
        assert inactive_user.is_active is True
        returned.refresh_from_db()
        assert returned.is_removed is True
        welcome_mock.assert_called_once_with(inactive_user)


class TestSendEmailVerification:
    @pytest.mark.django_db
    def test_calls_create_notification_with_expected_payload(self, mocker):
        # Arrange
        user = baker.make("users.User", email="user@example.com")
        code = "ABC123"
        verification_uuid = uuid.uuid4()
        create_notification_mock = mocker.patch("apps.verifications.services.create_notification")

        # Act
        send_email_verification(user, verification_uuid, code)

        # Assert
        expected_subject = "Confirma tu correo en PulseFit"
        expected_url = f"{settings.FRONTEND_URL.rstrip('/')}/#verify/{verification_uuid}/{code}"
        expected_message = (
            f"Confirma tu correo para activar tu cuenta: {expected_url} "
            f"(caduca en {settings.EMAIL_VERIFICATION_EXPIRATION_HOURS} horas)."
        )
        create_notification_mock.assert_called_once()
        kwargs = create_notification_mock.call_args.kwargs
        assert kwargs["subject"] == expected_subject
        assert kwargs["message"] == expected_message
        assert kwargs["recipient_list"] == [user]
        assert expected_url in (kwargs.get("html_content") or "")


class TestSendWelcomeEmail:
    @pytest.mark.django_db
    def test_calls_create_notification_with_welcome_template(self, mocker):
        user = baker.make("users.User", email="maria@example.com", first_name="María")
        create_notification_mock = mocker.patch("apps.verifications.services.create_notification")

        from apps.verifications.services import send_welcome_email

        send_welcome_email(user)

        kwargs = create_notification_mock.call_args.kwargs
        assert kwargs["subject"] == "Bienvenida a PulseFit, María"
        assert kwargs["recipient_list"] == [user]
        assert "Reservar mi primera clase" in (kwargs.get("html_content") or "")


class TestCreateVerificationCode:
    def test_uses_generator_and_triggers_email(self, mocker):
        # Arrange: patch code generator, model create, and email sender
        fake_user = mocker.Mock()
        created_obj = mocker.Mock(code="XYZ789", user=fake_user, id="uuid-123")
        create_mock = mocker.patch(
            "apps.verifications.services.VerificationCode.objects.create",
            return_value=created_obj,
        )
        email_mock = mocker.patch("apps.verifications.services.send_email_verification")
        gen_mock = mocker.patch(
            "apps.verifications.services.generate_verification_code",
            return_value="MOCKED1",
        )

        # Act
        result = create_verification_code(fake_user)

        # Assert: generator used and ORM called with its value
        gen_mock.assert_called_once_with()
        create_mock.assert_called_once_with(user=fake_user, code="MOCKED1", expires_at=mocker.ANY)

        # It should send the email with the id and code from the created object
        email_mock.assert_called_once_with(fake_user, created_obj.id, created_obj.code)

        # And return the created object
        assert result is created_obj


class TestGenerateVerificationCode:
    def test_returns_uppercase_alnum_of_expected_length(self):
        code = generate_verification_code()
        assert len(code) == constants.VERIFICATION_CODE_SIZE
        assert re.fullmatch(r"[A-Z0-9]{%d}" % constants.VERIFICATION_CODE_SIZE, code)
