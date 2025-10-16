"""Tests for the mailing module (sending emails from notifications)."""

import uuid

import pytest
from django.conf import settings
from model_bakery import baker

from apps.notifications.mailing import mark_notification_as_sent, send_pending_emails, Email
from apps.notifications import constants


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


class TestGetApiKeyForProvider:
    def test_returns_sendgrid_key(self, settings):
        settings.SENDGRID_API_KEY = "SG.TEST"
        settings.RESEND_API_KEY = "RS.TEST"
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email._get_api_key_for_provider(constants.MAIL_CLIENT_SENDGRID) == "SG.TEST"

    def test_returns_resend_key(self, settings):
        settings.SENDGRID_API_KEY = ""
        settings.RESEND_API_KEY = "RS.TEST"
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email._get_api_key_for_provider(constants.MAIL_CLIENT_RESEND) == "RS.TEST"

    def test_returns_none_for_unknown(self, settings):
        settings.SENDGRID_API_KEY = "SG.TEST"
        settings.RESEND_API_KEY = "RS.TEST"
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email._get_api_key_for_provider("unknown") is None


class TestEmailSendMail:
    def test_posts_payload_success(self, mocker, settings):
        # Arrange settings and client
        settings.SENDGRID_API_KEY = "SG.TEST"
        settings.DEFAULT_FROM_EMAIL = "from@example.com"
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
        )
        # Force client selection to sendgrid to keep assertions stable
        mocker.patch.object(
            Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_SENDGRID
        )

        # Mock requests.post to succeed
        resp = mocker.Mock()
        resp.status_code = 200
        resp.text = "ok"
        resp.raise_for_status.return_value = None
        post_mock = mocker.patch("apps.notifications.mailing.requests.post", return_value=resp)

        # Act
        email.send_mail()

        # Assert: called with expected payload and URL
        expected_json = {
            "provider": constants.MAIL_CLIENT_SENDGRID,
            "subject": "Hello",
            "message": "World",
            "recipient_list": ["to@example.com"],
            "from_email": "from@example.com",
            "api_key": "SG.TEST",
            "html_content": None,
        }
        post_mock.assert_called_once()
        args, kwargs = post_mock.call_args
        assert args[0] == constants.PYTHON_MAILING_URL
        assert kwargs["json"] == expected_json
        assert kwargs.get("timeout") == 20

        # No fallback should be triggered on success
        sendgrid_fallback = mocker.patch.object(Email, "send_sendgrid_email")
        resend_fallback = mocker.patch.object(Email, "send_resend_email")
        default_fallback = mocker.patch.object(Email, "send_default_email")
        sendgrid_fallback.assert_not_called()
        resend_fallback.assert_not_called()
        default_fallback.assert_not_called()

    def test_http_error_triggers_sendgrid_fallback(self, mocker, settings):
        # Arrange
        settings.SENDGRID_API_KEY = "SG.TEST"
        settings.DEFAULT_FROM_EMAIL = "from@example.com"
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
        )
        mocker.patch.object(
            Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_SENDGRID
        )

        # Mock post returns a response but raise_for_status raises HTTPError
        http_error = mocker.Mock(spec=mocker.ANY)
        resp = mocker.Mock()
        resp.text = "bad"
        resp.raise_for_status.side_effect = Exception("HTTP 500")
        post_mock = mocker.patch("apps.notifications.mailing.requests.post", return_value=resp)

        # Spy on fallbacks
        sendgrid_fallback = mocker.patch.object(Email, "send_sendgrid_email")
        resend_fallback = mocker.patch.object(Email, "send_resend_email")
        default_fallback = mocker.patch.object(Email, "send_default_email")

        # Act
        email.send_mail()

        # Assert: post called and sendgrid fallback used
        assert post_mock.called
        sendgrid_fallback.assert_called_once()
        resend_fallback.assert_not_called()
        default_fallback.assert_not_called()

    def test_http_error_triggers_resend_fallback(self, mocker, settings):
        # Arrange
        settings.RESEND_API_KEY = "RS.TEST"
        settings.DEFAULT_FROM_EMAIL = "from@example.com"
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
        )
        mocker.patch.object(Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_RESEND)

        # Mock post returns a response but raise_for_status raises HTTPError
        resp = mocker.Mock()
        resp.text = "bad"
        resp.raise_for_status.side_effect = Exception("HTTP 500")
        post_mock = mocker.patch("apps.notifications.mailing.requests.post", return_value=resp)

        # Spy on fallbacks
        sendgrid_fallback = mocker.patch.object(Email, "send_sendgrid_email")
        resend_fallback = mocker.patch.object(Email, "send_resend_email")
        default_fallback = mocker.patch.object(Email, "send_default_email")

        # Act
        email.send_mail()

        # Assert: post called and resend fallback used
        assert post_mock.called
        resend_fallback.assert_called_once()
        sendgrid_fallback.assert_not_called()
        default_fallback.assert_not_called()
