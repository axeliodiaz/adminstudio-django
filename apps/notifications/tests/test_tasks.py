"""Tests for notifications Celery tasks."""

from apps.notifications.tasks import async_send_notifications


class TestAsyncSendNotifications:
    def test_calls_send_pending_emails(self, mocker, mocked_pending):
        # Arrange
        send_emails_mock = mocker.patch("apps.notifications.tasks.send_pending_emails")

        # Act: call the task synchronously via .run()
        async_send_notifications.run(mocked_pending)

        # Assert
        send_emails_mock.assert_called_once_with(mocked_pending)
