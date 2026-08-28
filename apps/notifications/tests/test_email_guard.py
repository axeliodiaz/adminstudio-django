"""Guards that keep pytest from hitting the live mailing service / Sentry."""

import uuid

from apps.notifications.mailing import Email, send_pending_emails


def test_autouse_blocks_live_email_http(mocker):
    """Root conftest mocks Email.send_mail outside test_mailing.py."""
    post = mocker.patch("apps.notifications.mailing.requests.post")
    email = Email(
        notification_id="nid",
        subject="subj",
        message="msg",
        recipient_list=["to@example.com"],
        from_email="from@example.com",
    )

    email.send_mail()

    post.assert_not_called()


def test_autouse_blocks_send_pending_emails_http(mocker, settings):
    """Reservation/waitlist tests call create_notification → send_pending_emails."""
    post = mocker.patch("apps.notifications.mailing.requests.post")
    mocker.patch(
        "apps.notifications.mailing.get_user_from_id",
        return_value={"email": "wl_confirm_test@ex.com"},
    )
    mocker.patch("apps.notifications.mailing.mark_notification_as_sent")
    settings.RESEND_API_KEY = "should-not-be-used"

    send_pending_emails(
        [
            {
                "id": uuid.uuid4(),
                "subject": "Reserva confirmada · Clase · 22:16",
                "message": "msg",
                "user_id": uuid.uuid4(),
                "html_content": "",
                "recipient_list": [
                    {
                        "first_name": "Wait",
                        "last_name": "confirm",
                        "email": "wl_confirm_test@ex.com",
                    }
                ],
            }
        ]
    )

    post.assert_not_called()
