"""Guards that keep pytest from hitting the live mailing service / Sentry."""

from apps.notifications.mailing import Email


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
