"""Access tests for the Communications module shell (CYC-391)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

User = get_user_model()


@pytest.fixture
def member_client(api_client):
    member = User.objects.create_user(
        username="comms.member",
        email="comms.member@example.com",
        password="testpass123",
    )
    token = ExpiringToken.objects.create(user=member)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def staff_client(api_client):
    staff = User.objects.create_user(
        username="comms.admin",
        email="comms.admin@example.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
    )
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestCommunicationsModuleView:
    @pytest.fixture
    def url(self):
        return reverse("communications-module")

    def test_anonymous_is_rejected(self, api_client, url):
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_plain_staff_gets_403(self, api_client, url):
        user = User.objects.create_user(
            username="comms.plain.staff",
            email="comms.plain.staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        assert api_client.get(url).status_code == status.HTTP_403_FORBIDDEN

    def test_non_staff_member_gets_403(self, member_client, url):
        response = member_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_gets_module_info(self, staff_client, url):
        response = staff_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["module"] == "communications"
        assert payload["status"] == "active"
        assert payload["features"]["sending"] is False
