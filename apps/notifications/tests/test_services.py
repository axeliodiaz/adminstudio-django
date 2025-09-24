"""Tests for the notifications services."""

import pytest
from django.contrib.auth import get_user_model

from apps.notifications.services import create_notification, get_pending_notifications

User = get_user_model()


class TestCreateNotification:
    """Tests for the create_notification function."""

    @pytest.mark.django_db
    def test_create_notification(self, mocker, notification):
        """Test that the create_notification function works correctly."""
        # Arrange
        create_notification_mock = mocker.patch(
            "apps.notifications.notifications.create_notification"
        )
        async_send_notifications_mock = mocker.patch(
            "apps.notifications.tasks.async_send_notifications.delay"
        )

        # Act
        create_notification(notification.subject, notification.message, notification.user)

        # Assert
        create_notification_mock.assert_called_once_with(
            notification.subject, notification.message, notification.user
        )
        async_send_notifications_mock.assert_called_once()


class TestGetPendingNotifications:
    """Tests for the get_pending_notifications function."""

    def test_get_pending_notifications_transforms_to_schema(self, mocker, mocked_pending):
        """Test that the get_pending_notifications function transforms to schema."""
        # Arrange
        get_pending_mock = mocker.patch(
            "apps.notifications.notifications.get_pending_notifications",
            return_value=mocked_pending,
        )

        # Act
        result = get_pending_notifications()

        # Assert
        get_pending_mock.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == len(mocked_pending)
        for item, src in zip(result, mocked_pending):
            # Each item should be a Notification schema with the same fields
            assert item.id == src["id"]
            assert item.subject == src["subject"]
            assert item.message == src["message"]
            assert item.user_id == src["user_id"]
