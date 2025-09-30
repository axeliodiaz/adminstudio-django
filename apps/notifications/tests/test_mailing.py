"""Tests for the mailing module (sending emails from notifications)."""

import uuid

import pytest
from django.conf import settings
from model_bakery import baker

from apps.notifications.mailing import mark_notification_as_sent, send_pending_emails


class TestSendPendingEmails:
    def test_sends_email_and_marks_sent(self, mocker, mocked_pending):
        # Arrange: mock dependencies used inside send_pending_emails
        emails = ["user1@example.com", "user2@example.com"]
        get_user_from_id = mocker.patch(
            "apps.notifications.mailing.get_user_from_id",
            side_effect=[{"email": emails[0]}, {"email": emails[1]}],
        )
        email_send = mocker.patch("apps.notifications.mailing.Email.send_mail")
        mark_sent = mocker.patch("apps.notifications.mailing.mark_notification_as_sent")

        # Act
        send_pending_emails(mocked_pending)

        # Assert: get_user called for each, email client called, and marked sent
        assert get_user_from_id.call_count == len(mocked_pending)
        assert email_send.call_count == len(mocked_pending)
        for notification in mocked_pending:
            mark_sent.assert_any_call(str(notification["id"]))
        assert mark_sent.call_count == len(mocked_pending)

    def test_skips_when_no_email(self, mocker):
        # Arrange: a single pending notification and user without email
        notification = {
            "id": uuid.uuid4(),
            "subject": "Hi",
            "message": "There",
            "user_id": uuid.uuid4(),
            # Provide a valid recipient_list to satisfy Notification schema
            "recipient_list": [
                {
                    "first_name": "User",
                    "last_name": "Zero",
                    "email": "valid@example.com",
                    "phone_number": "",
                }
            ],
        }
        mocker.patch(
            "apps.notifications.mailing.get_user_from_id",
            return_value={"email": ""},
        )
        email_send = mocker.patch("apps.notifications.mailing.Email.send_mail")
        mark_sent = mocker.patch("apps.notifications.mailing.mark_notification_as_sent")

        # Act
        send_pending_emails([notification])

        # Assert: no email sent and not marked as sent
        email_send.assert_not_called()
        mark_sent.assert_not_called()


class TestMarkNotificationAsSent:
    @pytest.mark.django_db
    def test_updates_status_to_sent(self):
        # Arrange: create an enqueued notification
        notification = baker.make("notifications.Notification")
        assert notification.status == notification.STATUS.enqueued

        # Act
        mark_notification_as_sent(str(notification.id))

        # Assert
        notification.refresh_from_db()
        assert notification.status == notification.STATUS.sent
