"""Tests for the notifications services."""

import pytest
from django.contrib.auth import get_user_model

from apps.notifications.schemas import Notification as NotificationSchema
from apps.notifications.services import (
    create_notification,
    flush_pending_notifications,
    get_pending_notifications,
)

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
        send_pending_emails_mock = mocker.patch("apps.notifications.services.send_pending_emails")

        # Act
        create_notification(notification.subject, notification.message, notification.user)

        # Assert
        create_notification_mock.assert_called_once_with(
            notification.subject, notification.message, notification.user, html_content=None
        )
        send_pending_emails_mock.assert_called_once()


class TestGetPendingNotifications:
    """Tests for the get_pending_notifications function."""

    @pytest.mark.django_db
    def test_get_pending_notifications_transforms_to_schema(self, mocker, mocked_pending):
        """Test that the get_pending_notifications function transforms to schema."""
        # Arrange
        get_pending_mock = mocker.patch(
            "apps.notifications.notifications.get_pending_notifications",
            return_value=mocked_pending,
        )
        mocker.patch(
            "apps.notifications.services.get_user_from_id",
            return_value={
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone_number": "",
            },
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


class TestFlushPendingNotifications:
    """Tests for the flush_pending_notifications function."""

    @pytest.mark.django_db
    def test_flush_pending_notifications_sends_and_returns_count(self, mocker, mocked_pending):
        """Test that it sends every pending notification and returns how many."""
        # Arrange
        pending_schemas = [NotificationSchema(**item) for item in mocked_pending]
        mocker.patch(
            "apps.notifications.services.get_pending_notifications",
            return_value=pending_schemas,
        )
        send_pending_emails_mock = mocker.patch("apps.notifications.services.send_pending_emails")

        # Act
        result = flush_pending_notifications()

        # Assert
        assert result == len(mocked_pending)
        send_pending_emails_mock.assert_called_once_with(
            [notification.model_dump() for notification in pending_schemas]
        )

    @pytest.mark.django_db
    def test_flush_pending_notifications_with_none_pending(self, mocker):
        """Test that it handles the empty case without error."""
        mocker.patch(
            "apps.notifications.services.get_pending_notifications",
            return_value=[],
        )
        send_pending_emails_mock = mocker.patch("apps.notifications.services.send_pending_emails")

        result = flush_pending_notifications()

        assert result == 0
        send_pending_emails_mock.assert_called_once_with([])
