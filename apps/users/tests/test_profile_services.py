"""Tests for profile-related services in users app."""

import pytest
from datetime import date
from django.contrib.auth import get_user_model

from apps.users.services import get_user_profile, update_user_profile
from apps.users.schemas import UserProfileResponseSchema

User = get_user_model()


@pytest.mark.django_db
class TestGetUserProfile:
    def test_get_user_profile_returns_structured_schema(self):
        """Test that get_user_profile returns UserProfileResponseSchema."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass",
            first_name="Test",
            last_name="User",
            gender="male",
            birthdate=date(1990, 1, 1),
            height_cm=175,
            weight_kg=75.5,
            seat_height=17,
            cycling_shoe_size=44.0,
        )

        result = get_user_profile(user)

        assert isinstance(result, UserProfileResponseSchema)
        assert result.personal_info.first_name == "Test"
        assert result.personal_info.height_cm == 175
        assert result.cycling.seat_height == 17
        assert result.cycling.cycling_shoe_size == 44.0

    def test_get_user_profile_handles_empty_fields(self):
        """Test that get_user_profile handles None/empty values."""
        user = User.objects.create_user(
            username="emptyuser",
            email="empty@example.com",
            password="testpass",
        )

        result = get_user_profile(user)

        assert isinstance(result, UserProfileResponseSchema)
        assert result.personal_info.first_name is None or result.personal_info.first_name == ""
        assert result.personal_info.height_cm is None
        assert result.cycling.seat_height is None


@pytest.mark.django_db
class TestUpdateUserProfile:
    def test_update_user_profile_updates_personal_info(self):
        """Test that update_user_profile updates personal info fields."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass",
        )

        profile_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "gender": "female",
            "birthdate": date(1995, 5, 15),
            "height_cm": 180,
            "weight_kg": 80.0,
            "address": "New Address",
        }

        result = update_user_profile(user, profile_data)

        assert isinstance(result, UserProfileResponseSchema)
        assert result.personal_info.first_name == "Updated"
        assert result.personal_info.last_name == "Name"
        assert result.personal_info.gender == "female"
        assert result.personal_info.height_cm == 180

        # Verify data was saved
        user.refresh_from_db()
        assert user.first_name == "Updated"
        assert user.height_cm == 180

    def test_update_user_profile_updates_cycling_fields(self):
        """Test that update_user_profile updates cycling fields."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass",
        )

        profile_data = {
            "seat_height": 20,
            "seat_distance": 15,
            "handlebar_distance": 7,
            "cycling_shoe_size": 45.0,
        }

        result = update_user_profile(user, profile_data)

        assert isinstance(result, UserProfileResponseSchema)
        assert result.cycling.seat_height == 20
        assert result.cycling.seat_distance == 15
        assert result.cycling.handlebar_distance == 7
        assert result.cycling.cycling_shoe_size == 45.0

        # Verify data was saved
        user.refresh_from_db()
        assert user.seat_height == 20
        assert user.cycling_shoe_size == 45.0

    def test_update_user_profile_ignores_email_and_phone(self):
        """Test that update_user_profile ignores email and phone_number."""
        user = User.objects.create_user(
            username="testuser",
            email="original@example.com",
            password="testpass",
            phone_number="+1234567890",
        )

        original_email = user.email
        original_phone = user.phone_number

        profile_data = {
            "email": "newemail@example.com",
            "phone_number": "+9999999999",
            "first_name": "Updated",
        }

        result = update_user_profile(user, profile_data)

        # Should update first_name but not email/phone
        assert result.personal_info.first_name == "Updated"

        # Verify email and phone were NOT changed
        user.refresh_from_db()
        assert user.email == original_email
        assert user.phone_number == original_phone

    def test_update_user_profile_ignores_unknown_fields(self):
        """Test that update_user_profile ignores fields not in allowed_fields."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass",
        )

        profile_data = {
            "first_name": "Updated",
            "unknown_field": "should be ignored",
            "another_unknown": 123,
        }

        result = update_user_profile(user, profile_data)

        assert result.personal_info.first_name == "Updated"

        # Verify unknown fields were not set
        user.refresh_from_db()
        assert not hasattr(user, "unknown_field")
        assert not hasattr(user, "another_unknown")

    def test_update_user_profile_partial_update(self):
        """Test that update_user_profile works with partial updates."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass",
            first_name="Original",
            last_name="Name",
            height_cm=175,
        )

        # Only update first_name
        profile_data = {
            "first_name": "Updated",
        }

        result = update_user_profile(user, profile_data)

        assert result.personal_info.first_name == "Updated"
        # Other fields should remain unchanged
        assert result.personal_info.last_name == "Name"
        assert result.personal_info.height_cm == 175

        # Verify data was saved
        user.refresh_from_db()
        assert user.first_name == "Updated"
        assert user.last_name == "Name"  # Unchanged
        assert user.height_cm == 175  # Unchanged
