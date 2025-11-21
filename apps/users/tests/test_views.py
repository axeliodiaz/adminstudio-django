import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from drf_expiring_token.models import ExpiringToken

User = get_user_model()


@pytest.mark.django_db
class TestLoginView:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def user(self):
        """Create a test user with known credentials."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            phone_number="+1234567890",
        )
        return user

    @pytest.fixture
    def inactive_user(self):
        """Create an inactive test user."""
        user = User.objects.create_user(
            username="inactiveuser",
            email="inactive@example.com",
            password="testpass123",
        )
        user.is_active = False
        user.save()
        return user

    def test_login_successful_with_username(self, api_client, user):
        """Test successful login using username."""
        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert "token" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == "test@example.com"
        assert response.data["user"]["first_name"] == "Test"
        assert response.data["user"]["last_name"] == "User"
        assert response.data["user"]["username"] == "testuser"

        # Verify token was created
        token = ExpiringToken.objects.get(user=user)
        assert response.data["token"] == token.key

    def test_login_successful_with_email(self, api_client, user):
        """Test successful login using email instead of username."""
        url = reverse("users:login")
        payload = {
            "username": "test@example.com",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert "token" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == "test@example.com"

        # Verify token was created
        token = ExpiringToken.objects.get(user=user)
        assert response.data["token"] == token.key

    def test_login_returns_existing_token_if_already_exists(self, api_client, user):
        """Test that login returns existing token if one already exists."""
        # Create a token first
        existing_token = ExpiringToken.objects.create(user=user)
        existing_key = existing_token.key

        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert response.data["token"] == existing_key

        # Verify only one token exists
        assert ExpiringToken.objects.filter(user=user).count() == 1

    def test_login_fails_with_invalid_username(self, api_client, user):
        """Test login fails with non-existent username."""
        url = reverse("users:login")
        payload = {
            "username": "nonexistent",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 401
        assert "detail" in response.data
        assert response.data["detail"] == "Invalid credentials."

    def test_login_fails_with_invalid_password(self, api_client, user):
        """Test login fails with incorrect password."""
        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "wrongpassword",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 401
        assert "detail" in response.data
        assert response.data["detail"] == "Invalid credentials."

    def test_login_fails_with_inactive_user(self, api_client, inactive_user):
        """Test login fails for inactive users."""
        url = reverse("users:login")
        payload = {
            "username": "inactiveuser",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 401
        assert "detail" in response.data
        assert response.data["detail"] == "User account is disabled."

    def test_login_fails_without_username(self, api_client):
        """Test login fails when username is missing."""
        url = reverse("users:login")
        payload = {
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert "username" in str(response.data).lower()

    def test_login_fails_without_password(self, api_client):
        """Test login fails when password is missing."""
        url = reverse("users:login")
        payload = {
            "username": "testuser",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert "password" in str(response.data).lower()

    def test_login_fails_with_empty_payload(self, api_client):
        """Test login fails with empty payload."""
        url = reverse("users:login")
        payload = {}
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400

    def test_login_does_not_require_authentication(self, api_client, user):
        """Test that login endpoint is accessible without authentication."""
        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "testpass123",
        }
        # Make request without any authentication headers
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert "token" in response.data

    def test_token_has_expiration_date(self, api_client, user):
        """Test that tokens have an expiration date."""
        from django.utils import timezone
        from datetime import timedelta
        from django.conf import settings

        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        token = ExpiringToken.objects.get(user=user)
        assert token.expires is not None
        # Token should expire in the future
        assert token.expires > timezone.now()
        # Should be approximately configured lifespan from now (within 1 minute tolerance)
        expected_lifespan = getattr(settings, "EXPIRING_TOKEN_LIFESPAN", timedelta(hours=24))
        expected_expiry = timezone.now() + expected_lifespan
        assert abs((token.expires - expected_expiry).total_seconds()) < 60
