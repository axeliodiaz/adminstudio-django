"""Tests for the low-level notifications module functions."""

import pytest
from model_bakery import baker

from apps.notifications import notifications as notif_module
from apps.notifications.models import Notification


class TestCreateNotification:
    @pytest.mark.django_db
    def test_creates_notifications_for_all_recipients(self, recipients):
        # Arrange
        subject = "Subject"
        message = "Message"

        # Act
        notif_module.create_notification(subject, message, recipients)

        # Assert: one notification per recipient with default fields
        created = Notification.objects.filter(subject=subject, message=message)
        assert created.count() == len(recipients)

        # All created notifications should be for the intended users and enqueued by default
        created_user_ids = set(created.values_list("user_id", flat=True))
        assert created_user_ids == {u.id for u in recipients}
        assert all(notification.status == Notification.STATUS.enqueued for notification in created)
        assert all(
            notification.transport == Notification.TRANSPORT.mail for notification in created
        )


class TestGetPendingNotifications:
    @pytest.mark.django_db
    @pytest.mark.usefixtures("sent_notifications")
    def test_returns_only_enqueued_notifications_as_values(self, enqueued_notifications):
        # Arrange: fixtures provide enqueued and sent notifications
        expected_ids = {notification.id for notification in enqueued_notifications}

        # Act
        pending_values_qs = notif_module.get_pending_notifications()
        pending_list = list(pending_values_qs)

        # Assert: only enqueued returned and as dicts
        returned_ids = {item["id"] for item in pending_list}
        assert returned_ids == expected_ids
        assert all(item["status"] == Notification.STATUS.enqueued for item in pending_list)
        # ensure dict-like structure with expected keys
        sample = pending_list[0] if pending_list else None
        assert sample is None or {"id", "subject", "message", "user_id"}.issubset(sample.keys())


class TestMarkNotificationAsSent:
    @pytest.mark.django_db
    def test_updates_status_to_sent(self, notification):
        # Precondition
        assert notification.status == Notification.STATUS.enqueued

        # Act
        notif_module.mark_notification_as_sent(str(notification.id))

        # Assert
        notification.refresh_from_db()
        assert notification.status == Notification.STATUS.sent
