"""Tests for verifications services module."""

import re

import pytest
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
    def test_activates_user_and_soft_deletes_code(self, inactive_user, verification_code):
        # Precondition
        assert not inactive_user.is_active
        assert not verification_code.is_removed

        # Act
        returned = validate_code(verification_code)

        # Assert: user is activated and code soft-deleted
        inactive_user.refresh_from_db()
        assert inactive_user.is_active is True
        returned.refresh_from_db()
        assert returned.is_removed is True


class TestSendEmailVerification:
    @pytest.mark.django_db
    def test_calls_create_notification_with_expected_payload(self, mocker):
        # Arrange
        user = baker.make("users.User", email="user@example.com")
        code = "ABC123"
        create_notification_mock = mocker.patch("apps.verifications.services.create_notification")

        # Act
        send_email_verification(user, code)

        # Assert
        expected_subject = "Please confirm your subscription"
        expected_message = f"Your verification code is: {code}."
        create_notification_mock.assert_called_once_with(
            subject=expected_subject,
            message=expected_message,
            recipient_list=[user.email],
        )


class TestCreateVerificationCode:
    def test_uses_generator_and_triggers_email(self, mocker):
        # Arrange: patch code generator, model create, and email sender
        fake_user = mocker.Mock()
        created_obj = mocker.Mock(code="XYZ789", user=fake_user)
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
        create_mock.assert_called_once_with(user=fake_user, code="MOCKED1")

        # It should send the email with the code from the created object
        email_mock.assert_called_once_with(fake_user, created_obj.code)

        # And return the created object
        assert result is created_obj


class TestGenerateVerificationCode:
    def test_returns_uppercase_alnum_of_expected_length(self):
        code = generate_verification_code()
        assert len(code) == constants.VERIFICATION_CODE_SIZE
        assert re.fullmatch(r"[A-Z0-9]{%d}" % constants.VERIFICATION_CODE_SIZE, code)
