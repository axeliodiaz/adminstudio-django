"""Tests for instructors services module (using baker fixtures)."""

import uuid

import pytest
from django.core.exceptions import ObjectDoesNotExist

from apps.instructors.models import Instructor
from apps.instructors.services import (
    get_instructor_by_id,
    get_instructors_list,
    get_or_create_instructor_user,
    update_instructor,
)


@pytest.mark.django_db
class TestGetInstructorById:
    def test_returns_instructor_schema_dict_when_exists(self, instructor):
        # Act
        data = get_instructor_by_id(instructor.pk)

        # Assert: schema dict with expected keys and matching values
        assert isinstance(data, dict)
        # Accept either nested user or user_id depending on schema version
        assert "id" in data and "created" in data and "modified" in data
        assert ("user" in data) or ("user_id" in data)
        assert uuid.UUID(str(data["id"])) == instructor.id
        # If user_id exists, validate it; otherwise ensure nested user has email
        if "user_id" in data:
            assert uuid.UUID(str(data["user_id"])) == instructor.user.id
        else:
            assert isinstance(data["user"], dict)
            assert data["user"].get("email") == instructor.user.email
        assert data["created"] is not None
        assert data["modified"] is not None

    def test_raises_object_does_not_exist_with_friendly_message_when_missing(self):
        # Act / Assert
        with pytest.raises(ObjectDoesNotExist) as exc:
            get_instructor_by_id(uuid.uuid4())
        assert str(exc.value) == "Instructor not found."


@pytest.mark.django_db
class TestGetOrCreateInstructorUser:
    def test_creates_instructor_and_returns_user_schema_dict(self, validated_registration_data):
        # Act
        data, created = get_or_create_instructor_user(validated_registration_data)

        # Assert: created and payload matches UserSchema fields
        assert created is True
        assert set(data.keys()) == {"first_name", "last_name", "email", "phone_number"}
        assert data["email"] == validated_registration_data["email"]
        assert data["first_name"] == validated_registration_data["first_name"]
        assert data["last_name"] == validated_registration_data["last_name"]
        assert data["phone_number"] == validated_registration_data["phone_number"]
        # Ensure an Instructor was created and linked to the created user
        assert Instructor.objects.count() == 1

    def test_returns_existing_instructor_and_created_false_on_second_call(
        self, validated_registration_data
    ):
        # Arrange: first call creates the instructor
        _data, created_first = get_or_create_instructor_user(validated_registration_data)
        assert created_first is True

        # Act: second call with same email should fetch existing
        data, created_second = get_or_create_instructor_user(validated_registration_data)

        # Assert
        assert created_second is False
        assert Instructor.objects.count() == 1
        # Data should still be the same schema dict for the user
        assert set(data.keys()) == {"first_name", "last_name", "email", "phone_number"}
        assert data["email"] == validated_registration_data["email"]


@pytest.mark.django_db
class TestGetInstructorsList:
    def test_returns_list_of_instructor_schema_dicts(self, two_instructors):
        i1, i2 = two_instructors

        data = get_instructors_list()
        assert isinstance(data, list)
        ids = {str(item.get("id")) for item in data}
        assert str(i1.id) in ids and str(i2.id) in ids
        # Each item has id/created/modified and either user or user_id
        for item in data:
            assert "id" in item and "created" in item and "modified" in item
            assert ("user" in item) or ("user_id" in item)


@pytest.mark.django_db
class TestUpdateInstructor:
    def test_updates_user_fields_and_returns_schema_dict(self, instructor):
        # Ensure known initial state for one field
        instructor.user.first_name = "Old"
        instructor.user.save(update_fields=["first_name"])  # type: ignore[arg-type]

        payload = {
            "email": "updated@example.com",
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "phone_number": "+1777777777",
            "birthdate": "2001-01-01",
            "address": "Addr",
        }

        data = update_instructor(instructor.id, payload, partial=False)
        # Response shape
        assert "id" in data and "created" in data and "modified" in data
        assert ("user" in data) or ("user_id" in data)

        # DB changes
        instructor.user.refresh_from_db()
        assert instructor.user.email == payload["email"]
        assert instructor.user.first_name == payload["first_name"]
        assert instructor.user.last_name == payload["last_name"]
        assert instructor.user.phone_number == payload["phone_number"]

    def test_partial_update_only_updates_provided_fields(self, instructor):
        # Set a field to verify it remains unchanged
        instructor.user.first_name = "Keep"
        instructor.user.save(update_fields=["first_name"])  # type: ignore[arg-type]

        payload = {"phone_number": "+1666666666"}
        data = update_instructor(instructor.id, payload, partial=True)
        assert "id" in data
        instructor.user.refresh_from_db()
        assert instructor.user.first_name == "Keep"  # unchanged
        assert instructor.user.phone_number == "+1666666666"
