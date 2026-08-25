import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.studios.models import StudioSettings

User = get_user_model()


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="staff_settings",
        email="staff_settings@ex.com",
        password="pass",
        is_staff=True,
        is_superuser=False,
    )


@pytest.fixture
def superuser():
    return User.objects.create_superuser(
        username="super_settings",
        email="super_settings@ex.com",
        password="pass",
    )


@pytest.mark.django_db
class TestAdminStudioSettingsView:
    def test_staff_can_get_settings(self, api_client, staff_user):
        StudioSettings.load()
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("admin-studio-settings"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["free_cancellation_hours"] == 2

    def test_staff_cannot_patch_settings(self, api_client, staff_user):
        StudioSettings.load()
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.patch(
            reverse("admin-studio-settings"),
            {"free_cancellation_hours": 4},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_patch_settings(self, api_client, superuser):
        StudioSettings.load()
        token = ExpiringToken.objects.create(user=superuser)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.patch(
            reverse("admin-studio-settings"),
            {"free_cancellation_hours": 3},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["free_cancellation_hours"] == 3
        assert StudioSettings.load().free_cancellation_hours == 3
