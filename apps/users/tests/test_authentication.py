from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from drf_expiring_token.models import ExpiringToken
from drf_expiring_token.settings import custom_settings
from rest_framework.exceptions import AuthenticationFailed

from apps.users.authentication import ExpiringTokenAuthentication

User = get_user_model()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="testpass123",
        is_staff=True,
    )


@pytest.mark.django_db
class TestExpiringTokenAuthentication:
    def test_fresh_token_does_not_write(self, staff_user):
        token = ExpiringToken.objects.create(user=staff_user)
        auth = ExpiringTokenAuthentication()

        with patch.object(ExpiringToken, "save") as save:
            user, returned = auth.authenticate_credentials(token.key)

        assert user == staff_user
        assert returned.key == token.key
        save.assert_not_called()

    def test_extends_expiry_when_halfway_elapsed(self, staff_user):
        token = ExpiringToken.objects.create(user=staff_user)
        ExpiringToken.objects.filter(pk=token.pk).update(
            expires=timezone.now() + (custom_settings.EXPIRING_TOKEN_DURATION / 2),
        )
        auth = ExpiringTokenAuthentication()

        auth.authenticate_credentials(token.key)

        token.refresh_from_db()
        assert token.expires > timezone.now() + (custom_settings.EXPIRING_TOKEN_DURATION / 2)

    def test_expired_token_is_rejected(self, staff_user):
        token = ExpiringToken.objects.create(user=staff_user)
        ExpiringToken.objects.filter(pk=token.pk).update(
            expires=timezone.now() - timedelta(seconds=1),
        )
        auth = ExpiringTokenAuthentication()

        with pytest.raises(AuthenticationFailed):
            auth.authenticate_credentials(token.key)

    def test_admin_instructor_list_succeeds_for_staff(self, api_client, staff_user):
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("admin-instructors"))

        assert response.status_code == 200
        assert isinstance(response.data, list)
