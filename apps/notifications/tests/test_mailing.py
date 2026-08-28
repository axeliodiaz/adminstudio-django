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


class TestEmailFromAddress:
    def test_falls_back_to_noreply_at_email_domain(self, settings):
        settings.DEFAULT_FROM_EMAIL = None
        settings.EMAIL_DOMAIN = "pulsefit.com"
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email.from_email == "noreply@pulsefit.com"


class TestGetApiKeyForProvider:
    def test_returns_resend_key(self, settings):
        settings.RESEND_API_KEY = "RS.TEST"
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email._get_api_key_for_provider(constants.MAIL_CLIENT_RESEND) == "RS.TEST"

    def test_returns_none_for_unknown(self, settings):
        settings.RESEND_API_KEY = "RS.TEST"
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email._get_api_key_for_provider("unknown") is None


class TestGetMailingClient:
    def test_returns_resend_when_api_key_present(self, settings):
        settings.DEBUG = False
        settings.RESEND_API_KEY = "RS.TEST"
        settings.MAILTRAP_API_KEY = "MT.TEST"
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email.get_mailing_client() == constants.MAIL_CLIENT_RESEND

    def test_returns_mailtrap_when_configured(self, settings):
        settings.DEBUG = False
        settings.RESEND_API_KEY = None
        settings.MAILTRAP_API_KEY = "MT.TEST"
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email.get_mailing_client() == constants.MAIL_CLIENT_MAILTRAP

    def test_returns_mailtrap_in_debug_even_if_other_providers_present(self, settings):
        settings.DEBUG = True
        settings.RESEND_API_KEY = "RS.TEST"
        settings.MAILTRAP_API_KEY = "MT.TEST"
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email.get_mailing_client() == constants.MAIL_CLIENT_MAILTRAP

    def test_returns_default_when_no_providers_configured(self, settings):
        settings.DEBUG = False
        settings.RESEND_API_KEY = None
        settings.MAILTRAP_API_KEY = None
        settings.EMAIL_HOST = "localhost"
        settings.EMAIL_HOST_USER = None
        settings.EMAIL_HOST_PASSWORD = None
        email = Email(
            notification_id="nid",
            subject="subj",
            message="msg",
            recipient_list=["a@b.com"],
        )
        assert email.get_mailing_client() == constants.MAIL_CLIENT_DEFAULT


class TestEmailSendMail:
    def test_posts_payload_success(self, mocker, settings):
        settings.RESEND_API_KEY = "RS.TEST"
        settings.DEFAULT_FROM_EMAIL = "from@example.com"
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
        )
        mocker.patch.object(Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_RESEND)

        resp = mocker.Mock()
        resp.status_code = 200
        resp.text = "ok"
        resp.raise_for_status.return_value = None
        post_mock = mocker.patch("apps.notifications.mailing.requests.post", return_value=resp)

        email.send_mail()

        expected_json = {
            "provider": constants.MAIL_CLIENT_RESEND,
            "subject": "Hello",
            "message": "World",
            "recipient_list": ["to@example.com"],
            "from_email": "from@example.com",
            "api_key": "RS.TEST",
            "html_content": None,
        }
        post_mock.assert_called_once()
        args, kwargs = post_mock.call_args
        assert args[0] == constants.PYTHON_MAILING_URL
        assert kwargs["json"] == expected_json
        assert kwargs.get("timeout") == 60

    def test_http_error_handled_resend(self, mocker, settings):
        # Arrange
        import requests as requests_lib

        settings.RESEND_API_KEY = "RS.TEST"
        settings.DEFAULT_FROM_EMAIL = "from@example.com"
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
        )
        mocker.patch.object(Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_RESEND)

        # Upstream 503 (e.g. Render cold start) must not raise or use logger.exception
        resp = mocker.Mock()
        resp.text = "Service Unavailable"
        resp.status_code = 503
        http_error = requests_lib.exceptions.HTTPError(
            "503 Server Error: Service Unavailable", response=resp
        )
        resp.raise_for_status.side_effect = http_error
        post_mock = mocker.patch("apps.notifications.mailing.requests.post", return_value=resp)
        log_warning = mocker.patch("apps.notifications.mailing.logger.warning")
        log_exception = mocker.patch("apps.notifications.mailing.logger.exception")

        # Act - should not raise
        email.send_mail()

        # Assert: post called, soft-logged as warning (not exception → no Sentry issue)
        assert post_mock.called
        log_warning.assert_called_once()
        assert "Failed to send email via external service" in log_warning.call_args.args[0]
        log_exception.assert_not_called()

    def test_sends_via_api_for_mailtrap(self, mocker, settings):
        # Arrange
        settings.DEFAULT_FROM_EMAIL = "from@example.com"
        settings.MAILTRAP_API_KEY = "MT.TEST"
        settings.MAILTRAP_USE_SANDBOX = False
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
        )
        mocker.patch.object(
            Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_MAILTRAP
        )

        # Mock requests.post to succeed
        resp = mocker.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        post_mock = mocker.patch("apps.notifications.mailing.requests.post", return_value=resp)

        # Act
        email.send_mail()

        # Assert: HTTP POST was made to Mailtrap API
        post_mock.assert_called_once()
        args, kwargs = post_mock.call_args
        assert args[0] == constants.MAILTRAP_API_URL
        assert kwargs["headers"]["Authorization"] == "Bearer MT.TEST"
        assert kwargs["json"]["from"]["email"] == "from@example.com"
        assert kwargs["json"]["to"][0]["email"] == "to@example.com"
        assert kwargs["json"]["subject"] == "Hello"
        assert kwargs["json"]["text"] == "World"

    def test_sends_html_content_via_api_for_mailtrap(self, mocker, settings):
        # Arrange
        settings.DEFAULT_FROM_EMAIL = "from@example.com"
        settings.MAILTRAP_API_KEY = "MT.TEST"
        settings.MAILTRAP_USE_SANDBOX = False
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
            html_content="<html><body>Hello</body></html>",
        )
        mocker.patch.object(
            Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_MAILTRAP
        )

        # Mock requests.post
        resp = mocker.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        post_mock = mocker.patch("apps.notifications.mailing.requests.post", return_value=resp)

        # Act
        email.send_mail()

        # Assert: HTML content was included in payload
        post_mock.assert_called_once()
        args, kwargs = post_mock.call_args
        assert kwargs["json"]["html"] == "<html><body>Hello</body></html>"
        assert kwargs["json"]["text"] == "World"

    def test_api_error_handled_for_mailtrap(self, mocker, settings):
        # Arrange
        settings.DEFAULT_FROM_EMAIL = "from@example.com"
        settings.MAILTRAP_API_KEY = "MT.TEST"
        settings.MAILTRAP_USE_SANDBOX = False
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
        )
        mocker.patch.object(
            Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_MAILTRAP
        )

        # Mock requests.post to raise an exception
        post_mock = mocker.patch(
            "apps.notifications.mailing.requests.post",
            side_effect=Exception("API Error"),
        )

        # Act & Assert: exception should be raised (not swallowed)
        with pytest.raises(Exception, match="API Error"):
            email.send_mail()
        post_mock.assert_called_once()

    def test_skips_mailtrap_send_when_from_email_missing(self, mocker, settings):
        settings.DEFAULT_FROM_EMAIL = None
        settings.EMAIL_DOMAIN = None
        settings.MAILTRAP_API_KEY = "MT.TEST"
        settings.MAILTRAP_USE_SANDBOX = False
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
            from_email=None,
        )
        email.from_email = None
        mocker.patch.object(
            Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_MAILTRAP
        )
        post_mock = mocker.patch("apps.notifications.mailing.requests.post")

        email.send_mail()

        post_mock.assert_not_called()

    def test_uses_sandbox_url_when_configured(self, mocker, settings):
        settings.DEFAULT_FROM_EMAIL = "from@example.com"
        settings.MAILTRAP_API_KEY = "MT.TEST"
        settings.MAILTRAP_USE_SANDBOX = True
        settings.MAILTRAP_INBOX_ID = "509395"
        email = Email(
            notification_id="123",
            subject="Hello",
            message="World",
            recipient_list=["to@example.com"],
        )
        mocker.patch.object(
            Email, "get_mailing_client", return_value=constants.MAIL_CLIENT_MAILTRAP
        )
        resp = mocker.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        post_mock = mocker.patch("apps.notifications.mailing.requests.post", return_value=resp)

        email.send_mail()

        post_mock.assert_called_once()
        assert post_mock.call_args[0][0] == f"{constants.MAILTRAP_SANDBOX_API_URL}/509395"
