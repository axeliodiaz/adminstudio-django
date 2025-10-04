import uuid

import pytest
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.schedules.serializers import ScheduleCreateSerializer


class TestScheduleCreateSerializerValidateInstructorId:
    def test_raises_validation_error_when_instructor_missing(self, mocker):
        # Arrange: make the service raise ObjectDoesNotExist
        mocker.patch(
            "apps.schedules.serializers.get_instructor_by_id", side_effect=ObjectDoesNotExist
        )
        serializer = ScheduleCreateSerializer()
        fake_instructor_id = uuid.uuid4()

        # Act & Assert
        with pytest.raises(serializers.ValidationError) as exc:
            serializer.validate_instructor_id(fake_instructor_id)

        assert "Instructor not found." in str(exc.value)

    def test_returns_value_when_instructor_exists(self, mocker):
        # Arrange: service returns without raising
        spy = mocker.patch("apps.schedules.serializers.get_instructor_by_id", return_value={})
        serializer = ScheduleCreateSerializer(context={"enable_instructor_validation": True})
        fake_instructor_id = uuid.uuid4()

        # Act
        returned = serializer.validate_instructor_id(fake_instructor_id)

        # Assert: value is passed through and service was called with the same ID
        assert returned == fake_instructor_id
        spy.assert_called_once_with(fake_instructor_id)
