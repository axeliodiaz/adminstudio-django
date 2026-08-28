import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestFlushPendingNotificationsView:
    @pytest.fixture
    def url(self):
        return reverse("notifications-flush-pending")

    def test_missing_token_configured_returns_503(self, client, url, monkeypatch, mocker):
        monkeypatch.delenv("NOTIFICATIONS_CRON_TOKEN", raising=False)
        flush_mock = mocker.patch("apps.notifications.views.flush_pending_notifications")

        response = client.post(url, HTTP_X_CRON_TOKEN="anything")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        flush_mock.assert_not_called()

    def test_wrong_token_returns_401(self, client, url, monkeypatch, mocker):
        monkeypatch.setenv("NOTIFICATIONS_CRON_TOKEN", "correct-token")
        flush_mock = mocker.patch("apps.notifications.views.flush_pending_notifications")

        response = client.post(url, HTTP_X_CRON_TOKEN="wrong-token")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        flush_mock.assert_not_called()

    def test_missing_token_header_returns_401(self, client, url, monkeypatch, mocker):
        monkeypatch.setenv("NOTIFICATIONS_CRON_TOKEN", "correct-token")
        flush_mock = mocker.patch("apps.notifications.views.flush_pending_notifications")

        response = client.post(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        flush_mock.assert_not_called()

    def test_correct_token_flushes_and_returns_count(self, client, url, monkeypatch, mocker):
        monkeypatch.setenv("NOTIFICATIONS_CRON_TOKEN", "correct-token")
        flush_mock = mocker.patch(
            "apps.notifications.views.flush_pending_notifications", return_value=3
        )

        response = client.post(url, HTTP_X_CRON_TOKEN="correct-token")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"processed": 3}
        flush_mock.assert_called_once()
