from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken

from apps.members.models import Member
from apps.users.clerk import ClerkAuthError, ClerkProfile
from apps.users.services import exchange_clerk_session

User = get_user_model()


def _profile(**overrides):
    data = dict(
        clerk_user_id="user_abc",
        email="rider@example.com",
        first_name="Ana",
        last_name="Rider",
        phone_number="+56911111111",
    )
    data.update(overrides)
    return ClerkProfile(**data)


@pytest.mark.django_db
class TestExchangeClerkSession:
    def test_creates_active_member_and_token(self):
        with (
            patch(
                "apps.users.services.verify_clerk_session_token", return_value={"sub": "user_abc"}
            ),
            patch("apps.users.services.fetch_clerk_user", return_value=_profile()),
        ):
            user, token = exchange_clerk_session("jwt-token")

        assert user.email == "rider@example.com"
        assert user.is_active is True
        assert user.first_name == "Ana"
        assert Member.objects.filter(user=user).exists()
        assert token.user == user
        assert ExpiringToken.objects.filter(user=user).count() == 1

    def test_links_existing_email_and_activates(self):
        existing = User.objects.create_user(
            username="old@example.com",
            email="rider@example.com",
            password="pass1234",
            is_active=False,
        )
        with (
            patch(
                "apps.users.services.verify_clerk_session_token", return_value={"sub": "user_abc"}
            ),
            patch("apps.users.services.fetch_clerk_user", return_value=_profile()),
        ):
            user, token = exchange_clerk_session("jwt-token")

        assert user.id == existing.id
        user.refresh_from_db()
        assert user.is_active is True
        assert token.user == user

    def test_rejects_invalid_token(self):
        with patch(
            "apps.users.services.verify_clerk_session_token",
            side_effect=ClerkAuthError("Invalid Clerk session token"),
        ):
            with pytest.raises(ClerkAuthError):
                exchange_clerk_session("bad")


@pytest.mark.django_db
class TestClerkSessionView:
    def test_requires_bearer_token(self, api_client):
        url = reverse("users:clerk")
        response = api_client.post(url, {}, format="json")
        assert response.status_code == 401

    def test_returns_django_token(self, api_client):
        url = reverse("users:clerk")
        with (patch("apps.users.views.exchange_clerk_session") as exchange,):
            user = User.objects.create_user(
                username="rider@example.com",
                email="rider@example.com",
                password="pass1234",
                first_name="Ana",
            )
            token = ExpiringToken.objects.create(user=user)
            exchange.return_value = (user, token)
            response = api_client.post(
                url,
                {},
                format="json",
                HTTP_AUTHORIZATION="Bearer clerk-jwt",
            )

        assert response.status_code == 200
        assert response.data["token"] == token.key
        assert response.data["user"]["email"] == "rider@example.com"
        exchange.assert_called_once_with("clerk-jwt")
