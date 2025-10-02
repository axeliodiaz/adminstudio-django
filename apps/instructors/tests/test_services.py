"""Tests for instructors services module."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from apps.instructors.models import Instructor
from apps.instructors.services import get_instructor_by_id, get_or_create_instructor_user


@pytest.fixture
def validated_registration_data():
    return {
        "email": "jane.doe@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "phone_number": "+198765432",
        "password": "ignored_password",
    }


@pytest.mark.django_db
class TestGetInstructorById:
    def test_returns_instructor_schema_dict_when_exists(self):
        # Arrange: create a user and instructor
        User = get_user_model()
        user = User.objects.create_user(
            username="instructor_user",
            email="instructor@example.com",
            password="secret",
        )
        instructor = Instructor.objects.create(user=user)

        # Act
        data = get_instructor_by_id(instructor.pk)

        # Assert: schema dict with expected keys and matching values
        assert isinstance(data, dict)
        assert set(data.keys()) == {"id", "created", "modified", "user_id"}
        assert uuid.UUID(str(data["id"])) == instructor.id
        assert uuid.UUID(str(data["user_id"])) == user.id
        # created/modified should be ISO-serializable datetime strings when dumped by pydantic
        # but we only ensure they exist and are not None
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
