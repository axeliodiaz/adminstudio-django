"""Tests for VerificationView API endpoint."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.verifications.models import VerificationCode


@pytest.mark.django_db
class TestVerificationView:
    def setup_method(self):
        self.client = APIClient()

    def test_successful_verification_activates_user_and_soft_deletes(
        self, inactive_user, verification_code
    ):
        # Precondition
        assert inactive_user.is_active is False
        assert verification_code.is_removed is False

        # Act
        endpoint = reverse("verification", kwargs={"verification_uuid": str(verification_code.id)})
        resp = self.client.patch(
            endpoint,
            {
                "code": verification_code.code,
            },
            format="json",
        )

        # Assert
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["detail"] == "Email verified successfully."

        inactive_user.refresh_from_db()
        verification_code.refresh_from_db()
        assert inactive_user.is_active is True
        assert verification_code.is_removed is True

    def test_invalid_code_returns_400_and_no_side_effects(self, inactive_user, verification_code):
        # Act
        # Use a different 6-char code to avoid serializer max_length error
        wrong_last = "Z" if verification_code.code[-1] != "Z" else "Y"
        wrong_code = verification_code.code[:-1] + wrong_last
        endpoint = reverse("verification", kwargs={"verification_uuid": str(verification_code.id)})
        resp = self.client.patch(
            endpoint,
            {
                "code": wrong_code,  # wrong but same length
            },
            format="json",
        )

        # Assert
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["detail"] == "Invalid verification code."
        inactive_user.refresh_from_db()
        verification_code.refresh_from_db()
        assert inactive_user.is_active is False
        assert verification_code.is_removed is False

    def test_expired_code_returns_400(self, inactive_user):
        vc = baker.make(
            "verifications.VerificationCode",
            user=inactive_user,
            has_confirmed=False,
            is_removed=False,
            expires_at=timezone.now() - timedelta(minutes=1),  # already expired
        )

        endpoint = reverse("verification", kwargs={"verification_uuid": str(vc.id)})
        resp = self.client.patch(
            endpoint,
            {
                "code": vc.code,
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["detail"] == "Invalid verification code."

    def test_removed_code_returns_400(self, inactive_user):
        vc = baker.make(
            "verifications.VerificationCode",
            user=inactive_user,
            has_confirmed=False,
            is_removed=True,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        endpoint = reverse("verification", kwargs={"verification_uuid": str(vc.id)})
        resp = self.client.patch(
            endpoint,
            {
                "code": vc.code,
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["detail"] == "Invalid verification code."

    def test_already_confirmed_returns_400(self, inactive_user):
        vc = baker.make(
            "verifications.VerificationCode",
            user=inactive_user,
            has_confirmed=True,
            is_removed=False,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        endpoint = reverse("verification", kwargs={"verification_uuid": str(vc.id)})
        resp = self.client.patch(
            endpoint,
            {
                "code": vc.code,
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["detail"] == "Invalid verification code."
