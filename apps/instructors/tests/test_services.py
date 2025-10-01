"""Tests for instructors services module."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from apps.instructors.models import Instructor
from apps.instructors.services import get_instructor_by_id


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
