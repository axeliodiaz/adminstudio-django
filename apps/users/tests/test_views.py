import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from drf_expiring_token.models import ExpiringToken

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    """Create a test user with known credentials."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
        phone_number="+1234567890",
    )
    return user


@pytest.fixture
def inactive_user():
    """Create an inactive test user."""
    user = User.objects.create_user(
        username="inactiveuser",
        email="inactive@example.com",
        password="testpass123",
    )
    user.is_active = False
    user.save()
    return user


@pytest.mark.django_db
class TestLoginView:
    def test_login_successful_with_username(self, api_client, user):
        """Test successful login using username."""
        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert "token" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == "test@example.com"
        assert response.data["user"]["first_name"] == "Test"
        assert response.data["user"]["last_name"] == "User"
        assert response.data["user"]["username"] == "testuser"
        assert response.data["user"]["is_staff"] is False
        assert response.data["user"]["is_superuser"] is False
        assert response.data["user"]["is_coach"] is False

        # Verify token was created
        token = ExpiringToken.objects.get(user=user)
        assert response.data["token"] == token.key

    def test_login_successful_with_email(self, api_client, user):
        """Test successful login using email instead of username."""
        url = reverse("users:login")
        payload = {
            "username": "test@example.com",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert "token" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == "test@example.com"
        assert response.data["user"]["is_coach"] is False

        # Verify token was created
        token = ExpiringToken.objects.get(user=user)
        assert response.data["token"] == token.key

    def test_login_regenerates_token_each_time(self, api_client, user):
        """Test that login always regenerates token, deleting old ones."""
        # Create a token first
        existing_token = ExpiringToken.objects.create(user=user)
        existing_key = existing_token.key

        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        # Token should be different (regenerated)
        assert response.data["token"] != existing_key

        # Verify only one token exists (old one was deleted)
        assert ExpiringToken.objects.filter(user=user).count() == 1
        # And it's the new one
        new_token = ExpiringToken.objects.get(user=user)
        assert new_token.key == response.data["token"]

    def test_login_fails_with_invalid_username(self, api_client, user):
        """Test login fails with non-existent username."""
        url = reverse("users:login")
        payload = {
            "username": "nonexistent",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 401
        assert "detail" in response.data
        assert response.data["detail"] == "Invalid credentials."

    def test_login_fails_with_invalid_password(self, api_client, user):
        """Test login fails with incorrect password."""
        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "wrongpassword",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 401
        assert "detail" in response.data
        assert response.data["detail"] == "Invalid credentials."

    def test_login_fails_with_inactive_user(self, api_client, inactive_user):
        """Test login fails for inactive users."""
        url = reverse("users:login")
        payload = {
            "username": "inactiveuser",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 401
        assert "detail" in response.data
        assert response.data["detail"] == "User account is disabled."

    def test_login_fails_without_username(self, api_client):
        """Test login fails when username is missing."""
        url = reverse("users:login")
        payload = {
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert "username" in str(response.data).lower()

    def test_login_fails_without_password(self, api_client):
        """Test login fails when password is missing."""
        url = reverse("users:login")
        payload = {
            "username": "testuser",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert "password" in str(response.data).lower()

    def test_login_fails_with_empty_payload(self, api_client):
        """Test login fails with empty payload."""
        url = reverse("users:login")
        payload = {}
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400

    def test_login_does_not_require_authentication(self, api_client, user):
        """Test that login endpoint is accessible without authentication."""
        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "testpass123",
        }
        # Make request without any authentication headers
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert "token" in response.data

    def test_token_has_expiration_date(self, api_client, user):
        """Test that tokens have an expiration date."""
        from django.utils import timezone
        from datetime import timedelta
        from django.conf import settings

        url = reverse("users:login")
        payload = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        token = ExpiringToken.objects.get(user=user)
        assert token.expires is not None
        # Token should expire in the future
        assert token.expires > timezone.now()
        # Should be approximately configured lifespan from now (within 1 minute tolerance)
        expected_lifespan = getattr(settings, "EXPIRING_TOKEN_LIFESPAN", timedelta(hours=24))
        expected_expiry = timezone.now() + expected_lifespan
        assert abs((token.expires - expected_expiry).total_seconds()) < 60


@pytest.mark.django_db
class TestCurrentUserView:
    def test_me_requires_authentication(self, api_client):
        url = reverse("users:me")
        response = api_client.get(url)

        assert response.status_code == 401
        assert "detail" in response.data

    def test_me_returns_current_user(self, api_client, user):
        url = reverse("users:me")
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data["email"] == "test@example.com"
        assert response.data["first_name"] == "Test"
        assert response.data["last_name"] == "User"
        assert response.data["username"] == "testuser"
        assert response.data["phone_number"] == "+1234567890"
        assert response.data["is_staff"] is False
        assert response.data["is_superuser"] is False
        assert response.data["is_coach"] is False

    def test_me_returns_staff_flags(self, api_client):
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        url = reverse("users:me")
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data["email"] == "admin@example.com"
        assert response.data["is_staff"] is True
        assert response.data["is_superuser"] is True
        assert response.data["is_coach"] is False

    def test_me_returns_is_coach_for_instructor(self, api_client, user):
        from apps.instructors.models import Instructor

        Instructor.objects.create(user=user)
        url = reverse("users:me")
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data["is_coach"] is True


@pytest.mark.django_db
class TestAdminUserListView:
    def test_users_requires_authentication(self, api_client):
        url = reverse("users:users")
        response = api_client.get(url)

        assert response.status_code == 401

    def test_users_requires_staff(self, api_client, user):
        url = reverse("users:users")
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(url)

        assert response.status_code == 403

    def test_users_returns_list_for_staff(self, api_client, user):
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            is_staff=True,
        )
        url = reverse("users:users")
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(url)

        assert response.status_code == 200
        emails = {row["email"] for row in response.data}
        assert "test@example.com" in emails
        assert "admin@example.com" in emails
        assert "is_staff" in response.data[0]
        assert "last_login" in response.data[0]

    def test_users_filters_by_role_and_search(self, api_client, user):
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            is_staff=True,
        )
        url = reverse("users:users")
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        staff_response = api_client.get(url, {"role": "staff"})
        assert staff_response.status_code == 200
        assert all(row["is_staff"] is True for row in staff_response.data)
        assert len(staff_response.data) == 1

        search_response = api_client.get(url, {"search": "testuser"})
        assert search_response.status_code == 200
        assert [row["email"] for row in search_response.data] == ["test@example.com"]


@pytest.mark.django_db
class TestAdminUserDetailView:
    def test_user_detail_requires_staff(self, api_client, user):
        url = reverse("users:user-detail", kwargs={"user_id": user.id})
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(url)

        assert response.status_code == 403

    def test_user_detail_returns_user_for_staff(self, api_client, user):
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        url = reverse("users:user-detail", kwargs={"user_id": user.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data["email"] == "test@example.com"
        assert response.data["id"] == str(user.id)

    def test_user_detail_updates_fields(self, api_client, user):
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        url = reverse("users:user-detail", kwargs={"user_id": user.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.patch(
            url,
            data={
                "first_name": "Ana",
                "last_name": "Pérez",
                "phone_number": "+56911111111",
                "gender": "female",
                "is_staff": True,
                "is_active": True,
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["first_name"] == "Ana"
        assert response.data["last_name"] == "Pérez"
        assert response.data["phone_number"] == "+56911111111"
        assert response.data["gender"] == "female"
        assert response.data["is_staff"] is True
        user.refresh_from_db()
        assert user.first_name == "Ana"
        assert user.is_staff is True

    def test_user_cannot_remove_own_staff(self, api_client):
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        url = reverse("users:user-detail", kwargs={"user_id": staff_user.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.patch(url, data={"is_staff": False}, format="json")

        assert response.status_code == 400
        staff_user.refresh_from_db()
        assert staff_user.is_staff is True

    def test_staff_cannot_edit_superuser(self, api_client):
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        superuser = User.objects.create_user(
            username="root",
            email="root@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        url = reverse("users:user-detail", kwargs={"user_id": superuser.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        get_response = api_client.get(url)
        patch_response = api_client.patch(url, data={"first_name": "Root"}, format="json")

        assert get_response.status_code == 403
        assert patch_response.status_code == 403


@pytest.mark.django_db
class TestAdminUserEmailChangeView:
    def test_email_change_requires_staff(self, api_client, user):
        url = reverse("users:user-email-change", kwargs={"user_id": user.id})
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.post(url, data={"email": "nuevo@example.com"}, format="json")

        assert response.status_code == 403

    def test_staff_can_request_email_change_without_updating_current(
        self, api_client, user, mocker
    ):
        send_email_mock = mocker.patch("apps.users.services.send_email_change_email")
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        url = reverse("users:user-email-change", kwargs={"user_id": user.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.post(url, data={"email": "nuevo@example.com"}, format="json")

        assert response.status_code == 200
        assert response.data["pending_email"] == "nuevo@example.com"
        user.refresh_from_db()
        assert user.email == "test@example.com"
        send_email_mock.assert_called_once()

    def test_staff_cannot_patch_email_directly(self, api_client, user):
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        url = reverse("users:user-detail", kwargs={"user_id": user.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.patch(url, data={"email": "nuevo@example.com"}, format="json")

        assert response.status_code == 400
        user.refresh_from_db()
        assert user.email == "test@example.com"

    def test_staff_patch_keeps_same_email(self, api_client, user):
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        url = reverse("users:user-detail", kwargs={"user_id": user.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.patch(
            url,
            data={"email": "test@example.com", "first_name": "Ana"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["first_name"] == "Ana"
        assert response.data["email"] == "test@example.com"


@pytest.mark.django_db
class TestEmailChangeConfirmView:
    def test_confirm_updates_email(self, api_client, user):
        from datetime import timedelta

        from django.utils import timezone

        from apps.users.models import EmailChangeRequest

        change = EmailChangeRequest.objects.create(
            user=user,
            new_email="nuevo@example.com",
            code="ABC123",
            expires_at=timezone.now() + timedelta(hours=24),
        )
        url = reverse("users:email-change-confirm", kwargs={"change_uuid": change.id})

        response = api_client.patch(url, data={"code": "abc123"}, format="json")

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.email == "nuevo@example.com"
        assert EmailChangeRequest.objects.filter(id=change.id, is_removed=False).count() == 0

    def test_confirm_fails_with_invalid_code(self, api_client, user):
        from datetime import timedelta

        from django.utils import timezone

        from apps.users.models import EmailChangeRequest

        change = EmailChangeRequest.objects.create(
            user=user,
            new_email="nuevo@example.com",
            code="ABC123",
            expires_at=timezone.now() + timedelta(hours=24),
        )
        url = reverse("users:email-change-confirm", kwargs={"change_uuid": change.id})

        response = api_client.patch(url, data={"code": "XXXXXX"}, format="json")

        assert response.status_code == 400
        user.refresh_from_db()
        assert user.email == "test@example.com"


@pytest.mark.django_db
class TestAdminUserPasswordRecoveryView:
    def test_password_recovery_requires_staff(self, api_client, user):
        url = reverse("users:user-password-recovery", kwargs={"user_id": user.id})
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.post(url, format="json")

        assert response.status_code == 403

    def test_staff_can_send_password_recovery(self, api_client, user, mocker):
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        url = reverse("users:user-password-recovery", kwargs={"user_id": user.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.post(url, format="json")

        assert response.status_code == 200
        assert "Se envió un código de recuperación" in response.data["detail"]
        send_email_mock.assert_called_once()

    def test_staff_cannot_send_password_recovery_for_superuser(self, api_client, mocker):
        mocker.patch("apps.users.services.send_password_recovery_email")
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        superuser = User.objects.create_user(
            username="root",
            email="root@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        url = reverse("users:user-password-recovery", kwargs={"user_id": superuser.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.post(url, format="json")

        assert response.status_code == 403

    def test_staff_cannot_send_password_recovery_for_inactive_user(
        self, api_client, inactive_user, mocker
    ):
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")
        staff_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        url = reverse("users:user-password-recovery", kwargs={"user_id": inactive_user.id})
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.post(url, format="json")

        assert response.status_code == 400
        assert "cuenta inactiva" in response.data["detail"]
        send_email_mock.assert_not_called()


@pytest.mark.django_db
class TestChangePasswordView:
    def test_change_password_requires_authentication(self, api_client):
        url = reverse("users:change-password")
        payload = {
            "old_password": "oldpassword123",
            "new_password": "newpassword456",
        }

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 401

    def test_change_password_success_with_valid_current_password(self, api_client, user):
        url = reverse("users:change-password")
        payload = {
            "old_password": "testpass123",
            "new_password": "newpass456",
        }

        api_client.force_authenticate(user=user)
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert response.data["detail"] == "Contraseña actualizada."

        user.refresh_from_db()
        assert user.check_password("newpass456")

    def test_change_password_fails_with_invalid_current_password(self, api_client, user):
        url = reverse("users:change-password")
        payload = {
            "old_password": "wrongpassword",
            "new_password": "newpass456",
        }

        api_client.force_authenticate(user=user)
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert response.data["detail"] == "Contraseña actual incorrecta."


@pytest.mark.django_db
class TestPasswordRecoveryRequestView:
    def test_password_recovery_request_success(self, api_client, user, mocker):
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")
        url = reverse("users:password-recovery-request")
        payload = {"email": "test@example.com"}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert "Si el correo electrónico existe" in response.data["detail"]
        send_email_mock.assert_called_once()

    def test_password_recovery_request_does_not_expose_nonexistent_email(self, api_client, mocker):
        send_email_mock = mocker.patch("apps.users.services.send_password_recovery_email")
        url = reverse("users:password-recovery-request")
        payload = {"email": "nonexistent@example.com"}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert "Si el correo electrónico existe" in response.data["detail"]
        send_email_mock.assert_not_called()

    def test_password_recovery_request_requires_email(self, api_client):
        url = reverse("users:password-recovery-request")
        payload = {}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert "email" in str(response.data).lower()

    def test_password_recovery_request_validates_email_format(self, api_client):
        url = reverse("users:password-recovery-request")
        payload = {"email": "invalid-email"}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400

    def test_password_recovery_request_does_not_require_authentication(
        self, api_client, user, mocker
    ):
        mocker.patch("apps.users.services.send_password_recovery_email")
        url = reverse("users:password-recovery-request")
        payload = {"email": "test@example.com"}

        # Make request without any authentication headers
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200


@pytest.mark.django_db
class TestPasswordRecoveryConfirmView:
    def test_password_recovery_confirm_success(self, api_client, user):
        from apps.users.models import PasswordResetCode
        from django.utils import timezone
        from datetime import timedelta

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        url = reverse("users:password-recovery-confirm")
        payload = {"code": "ABC123", "new_password": "newpass456"}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        assert "Contraseña actualizada exitosamente" in response.data["detail"]
        user.refresh_from_db()
        assert user.check_password("newpass456")
        # Code should be invalidated
        assert PasswordResetCode.objects.filter(code="ABC123", is_removed=False).count() == 0

    def test_password_recovery_confirm_fails_with_invalid_code(self, api_client, user):
        url = reverse("users:password-recovery-confirm")
        payload = {"code": "XXXXXX", "new_password": "newpass456"}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert "Código inválido o expirado" in response.data["detail"]

    def test_password_recovery_confirm_fails_with_expired_code(self, api_client, user):
        from apps.users.models import PasswordResetCode
        from django.utils import timezone
        from datetime import timedelta

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() - timedelta(minutes=1),  # Expired
        )
        url = reverse("users:password-recovery-confirm")
        payload = {"code": "ABC123", "new_password": "newpass456"}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert "Código inválido o expirado" in response.data["detail"]

    def test_password_recovery_confirm_requires_code(self, api_client):
        url = reverse("users:password-recovery-confirm")
        payload = {"new_password": "newpass456"}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert "code" in str(response.data).lower()

    def test_password_recovery_confirm_requires_new_password(self, api_client):
        url = reverse("users:password-recovery-confirm")
        payload = {"code": "ABC123"}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400
        assert (
            "new_password" in str(response.data).lower() or "password" in str(response.data).lower()
        )

    def test_password_recovery_confirm_validates_password_strength(self, api_client, user):
        from apps.users.models import PasswordResetCode
        from django.utils import timezone
        from datetime import timedelta

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        url = reverse("users:password-recovery-confirm")
        payload = {"code": "ABC123", "new_password": "123"}  # Too short

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 400

    def test_password_recovery_confirm_does_not_require_authentication(self, api_client, user):
        from apps.users.models import PasswordResetCode
        from django.utils import timezone
        from datetime import timedelta

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        url = reverse("users:password-recovery-confirm")
        payload = {"code": "ABC123", "new_password": "newpass456"}

        # Make request without any authentication headers
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200

    def test_password_recovery_confirm_normalizes_code_to_uppercase(self, api_client, user):
        from apps.users.models import PasswordResetCode
        from django.utils import timezone
        from datetime import timedelta

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code="ABC123",
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        url = reverse("users:password-recovery-confirm")
        payload = {"code": "abc123", "new_password": "newpass456"}  # Lowercase

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("newpass456")
