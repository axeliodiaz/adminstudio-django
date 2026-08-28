import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestProcessPendingNotificationsCommand:
    def test_command_calls_flush_and_reports_count(self, mocker, capsys):
        flush_mock = mocker.patch(
            "apps.notifications.management.commands.process_pending_notifications."
            "flush_pending_notifications",
            return_value=2,
        )

        call_command("process_pending_notifications")

        flush_mock.assert_called_once_with()
        captured = capsys.readouterr()
        assert "Processed 2 pending notification(s)." in captured.out
