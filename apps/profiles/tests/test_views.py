"""Tests for profiles views."""

import pytest
from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from drf_expiring_token.models import ExpiringToken

User = get_user_model()


@pytest.mark.django_db
class TestProfileView:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def user(self):
        """Create a test user with profile data."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            phone_number="+1234567890",
            gender="male",
            birthdate=date(1990, 1, 1),
            height_cm=175,
            weight_kg=75.5,
            address="Test Address 123",
            injury_notes="Rodilla derecha sensible",
            seat_height=17,
            seat_distance=13,
            handlebar_distance=5,
            cycling_shoe_size=44.0,
        )
        return user

    @pytest.fixture
    def user_with_member(self, user):
        """Create a member for the user."""
        from apps.members.models import Member

        member, _ = Member.objects.get_or_create(user=user)
        return user

    @pytest.fixture
    def token(self, user):
        """Create an authentication token for the user."""
        return ExpiringToken.objects.create(user=user)

    def test_get_profile_requires_authentication(self, api_client):
        """Test that GET profile endpoint requires authentication."""
        url = reverse("profile-me")
        response = api_client.get(url)

        assert response.status_code == 401
        assert "detail" in response.data

    def test_get_profile_returns_structured_data(self, api_client, user_with_member, token):
        """Test that GET profile returns data structured by categories."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        url = reverse("profile-me")
        response = api_client.get(url)

        assert response.status_code == 200
        assert "personal_info" in response.data
        assert "cycling" in response.data
        assert "preferences" in response.data
        assert response.data["preferences"]["waitlist_auto_confirm"] is False

        # Check personal_info structure
        personal_info = response.data["personal_info"]
        assert str(personal_info["id"]) == str(user_with_member.id)
        assert personal_info["username"] == "testuser"
        assert personal_info["email"] == "test@example.com"
        assert personal_info["first_name"] == "Test"
        assert personal_info["last_name"] == "User"
        assert personal_info["phone_number"] == "+1234567890"
        assert personal_info["gender"] == "male"
        # birthdate can be date object or string depending on serialization
        assert str(personal_info["birthdate"]) == "1990-01-01" or personal_info[
            "birthdate"
        ] == date(1990, 1, 1)
        assert personal_info["height_cm"] == 175
        assert personal_info["weight_kg"] == 75.5
        assert personal_info["address"] == "Test Address 123"
        assert personal_info["injury_notes"] == "Rodilla derecha sensible"

        # Check cycling structure
        cycling = response.data["cycling"]
        assert cycling["seat_height"] == 17
        assert cycling["seat_distance"] == 13
        assert cycling["handlebar_distance"] == 5
        assert cycling["cycling_shoe_size"] == 44.0

    def test_get_profile_returns_empty_values_when_not_set(
        self, api_client, user_with_member, token
    ):
        """Test that GET profile returns None/empty values for unset fields."""
        # Create user without profile data
        empty_user = User.objects.create_user(
            username="emptyuser",
            email="empty@example.com",
            password="testpass123",
        )
        from apps.members.models import Member

        Member.objects.get_or_create(user=empty_user)
        empty_token = ExpiringToken.objects.create(user=empty_user)

        api_client.credentials(HTTP_AUTHORIZATION=f"Token {empty_token.key}")
        url = reverse("profile-me")
        response = api_client.get(url)

        assert response.status_code == 200
        assert "personal_info" in response.data
        assert "cycling" in response.data
        assert response.data["preferences"]["waitlist_auto_confirm"] is False

        personal_info = response.data["personal_info"]
        assert personal_info["first_name"] is None or personal_info["first_name"] == ""
        assert personal_info["height_cm"] is None
        assert personal_info["weight_kg"] is None

        cycling = response.data["cycling"]
        assert cycling["seat_height"] is None
        assert cycling["cycling_shoe_size"] is None

    def test_update_profile_requires_authentication(self, api_client):
        """Test that PUT/PATCH profile endpoint requires authentication."""
        url = reverse("profile-me")
        response = api_client.put(url, data={}, format="json")

        assert response.status_code == 401

    def test_update_profile_with_put(self, api_client, user_with_member, token):
        """Test that PUT updates profile data."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        url = reverse("profile-me")

        payload = {
            "first_name": "Updated",
            "last_name": "Name",
            "gender": "female",
            "birthdate": "1995-05-15",
            "height_cm": 180,
            "weight_kg": 80.0,
            "address": "New Address",
            "injury_notes": "Molestia lumbar",
            "seat_height": 20,
            "seat_distance": 15,
            "handlebar_distance": 7,
            "cycling_shoe_size": 45.0,
        }

        response = api_client.put(url, data=payload, format="json")

        assert response.status_code == 200
        assert response.data["personal_info"]["first_name"] == "Updated"
        assert response.data["personal_info"]["last_name"] == "Name"
        assert response.data["personal_info"]["gender"] == "female"
        assert response.data["personal_info"]["height_cm"] == 180
        assert response.data["personal_info"]["injury_notes"] == "Molestia lumbar"
        assert response.data["cycling"]["seat_height"] == 20
        assert response.data["cycling"]["cycling_shoe_size"] == 45.0

        # Verify data was saved
        user_with_member.refresh_from_db()
        assert user_with_member.first_name == "Updated"
        assert user_with_member.seat_height == 20
        assert user_with_member.injury_notes == "Molestia lumbar"

    def test_update_profile_with_patch(self, api_client, user_with_member, token):
        """Test that PATCH partially updates profile data."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        url = reverse("profile-me")

        # Only update some fields
        payload = {
            "first_name": "Patched",
            "seat_height": 25,
        }

        response = api_client.patch(url, data=payload, format="json")

        assert response.status_code == 200
        assert response.data["personal_info"]["first_name"] == "Patched"
        # Other fields should remain unchanged
        assert response.data["personal_info"]["last_name"] == "User"
        assert response.data["cycling"]["seat_height"] == 25
        # Original value should be preserved
        assert response.data["cycling"]["seat_distance"] == 13

        # Verify data was saved
        user_with_member.refresh_from_db()
        assert user_with_member.first_name == "Patched"
        assert user_with_member.seat_height == 25
        assert user_with_member.last_name == "User"  # Unchanged

    def test_update_profile_rejects_email_and_phone(self, api_client, user_with_member, token):
        """Test that email and phone_number cannot be updated via profile endpoint."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        url = reverse("profile-me")

        original_email = user_with_member.email
        original_phone = user_with_member.phone_number

        payload = {
            "email": "newemail@example.com",
            "phone_number": "+9999999999",
            "first_name": "Updated",
        }

        response = api_client.patch(url, data=payload, format="json")

        # Should succeed but email and phone should be ignored
        assert response.status_code == 200
        assert response.data["personal_info"]["first_name"] == "Updated"

        # Verify email and phone were NOT changed
        user_with_member.refresh_from_db()
        assert user_with_member.email == original_email
        assert user_with_member.phone_number == original_phone

    def test_update_profile_validates_cycling_fields(self, api_client, user_with_member, token):
        """Test that cycling fields are validated correctly."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        url = reverse("profile-me")

        payload = {
            "seat_height": -5,  # Invalid: negative
            "cycling_shoe_size": -10.0,  # Invalid: negative
        }

        response = api_client.patch(url, data=payload, format="json")

        assert response.status_code == 400  # Validation error

    def test_update_profile_allows_null_cycling_fields(self, api_client, user_with_member, token):
        """Test that cycling fields can be set to null."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        url = reverse("profile-me")

        payload = {
            "seat_height": None,
            "cycling_shoe_size": None,
        }

        response = api_client.patch(url, data=payload, format="json")

        assert response.status_code == 200
        assert response.data["cycling"]["seat_height"] is None
        assert response.data["cycling"]["cycling_shoe_size"] is None

        # Verify data was saved
        user_with_member.refresh_from_db()
        assert user_with_member.seat_height is None
        assert user_with_member.cycling_shoe_size is None
