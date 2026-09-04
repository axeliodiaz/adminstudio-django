import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.referrals.services import attribute_signup, get_or_create_referral_code

User = get_user_model()


@pytest.mark.django_db
class TestReferralViews:
    def test_click_records_valid_code(self, api_client, user):
        code = get_or_create_referral_code(user=user)

        response = api_client.post(reverse("referral-click"), {"code": code.code}, format="json")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_dashboard_returns_member_code_and_progress(self, api_client, user):
        referred = User.objects.create_user(
            username="invited",
            email="invited@example.com",
            password="password",
        )
        code = get_or_create_referral_code(user=user)
        attribute_signup(referred_user=referred, code=code.code)
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("referral-me"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == code.code
        assert response.data["pending_count"] == 1

    def test_admin_dashboard_requires_staff(self, api_client, user):
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("referral-admin-dashboard"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
