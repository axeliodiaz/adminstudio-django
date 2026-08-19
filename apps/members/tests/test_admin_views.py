"""API tests for staff admin member endpoints."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken

from apps.members.models import Member
from apps.wallets.models import Wallet

User = get_user_model()


@pytest.fixture
def staff_client(api_client):
    staff_user = User.objects.create_user(
        username="adminuser",
        email="admin@example.com",
        password="testpass123",
        is_staff=True,
    )
    token = ExpiringToken.objects.create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client, staff_user


@pytest.fixture
def member_user(db):
    user = User.objects.create_user(
        username="socio@example.com",
        email="socio@example.com",
        password="pass1234",
        first_name="Ana",
        last_name="Ríos",
        phone_number="+56911112222",
        gender="female",
    )
    member = Member.objects.create(user=user)
    Wallet.objects.create(user=user, class_credits=5)
    return member


@pytest.mark.django_db
class TestAdminMemberListView:
    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse("admin-members"))
        assert response.status_code == 401

    def test_requires_staff(self, api_client, member_user):
        token = ExpiringToken.objects.create(user=member_user.user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("admin-members"))
        assert response.status_code == 403

    def test_returns_list_for_staff(self, staff_client, member_user):
        client, _ = staff_client
        response = client.get(reverse("admin-members"))

        assert response.status_code == 200
        ids = {row["id"] for row in response.data}
        assert str(member_user.id) in ids
        match = next(row for row in response.data if row["id"] == str(member_user.id))
        assert match["email"] == "socio@example.com"
        assert match["class_credits"] == 5
        assert match["first_name"] == "Ana"

    def test_filters_by_status_and_search(self, staff_client, member_user):
        client, _ = staff_client
        inactive_user = User.objects.create_user(
            username="inactive@example.com",
            email="inactive@example.com",
            password="pass1234",
            first_name="Bob",
            is_active=False,
        )
        Member.objects.create(user=inactive_user)

        active_response = client.get(reverse("admin-members"), {"status": "active"})
        assert active_response.status_code == 200
        assert all(row["is_active"] is True for row in active_response.data)
        assert str(member_user.id) in {row["id"] for row in active_response.data}

        search_response = client.get(reverse("admin-members"), {"search": "Ana"})
        assert search_response.status_code == 200
        assert [row["email"] for row in search_response.data] == ["socio@example.com"]

    def test_create_member(self, staff_client):
        client, _ = staff_client
        response = client.post(
            reverse("admin-members"),
            data={
                "email": "nuevo@example.com",
                "password": "Secret123!",
                "first_name": "Luna",
                "last_name": "Pérez",
                "phone_number": "+56999998888",
                "gender": "female",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["email"] == "nuevo@example.com"
        assert response.data["first_name"] == "Luna"
        assert response.data["gender"] == "female"
        assert Member.objects.filter(user__email="nuevo@example.com").exists()


@pytest.mark.django_db
class TestAdminMemberDetailView:
    def test_detail_requires_staff(self, api_client, member_user):
        token = ExpiringToken.objects.create(user=member_user.user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(
            reverse("admin-member-detail", kwargs={"member_id": member_user.id})
        )
        assert response.status_code == 403

    def test_detail_returns_member(self, staff_client, member_user):
        client, _ = staff_client
        response = client.get(reverse("admin-member-detail", kwargs={"member_id": member_user.id}))

        assert response.status_code == 200
        assert response.data["id"] == str(member_user.id)
        assert response.data["email"] == member_user.user.email
        assert response.data["class_credits"] == 5

    def test_patch_updates_fields(self, staff_client, member_user):
        client, _ = staff_client
        url = reverse("admin-member-detail", kwargs={"member_id": member_user.id})
        response = client.patch(
            url,
            data={
                "first_name": "Anita",
                "phone_number": "+56900001111",
                "is_active": False,
                "gender": "other",
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["first_name"] == "Anita"
        assert response.data["phone_number"] == "+56900001111"
        assert response.data["is_active"] is False
        assert response.data["gender"] == "other"

        member_user.user.refresh_from_db()
        assert member_user.user.first_name == "Anita"
        assert member_user.user.is_active is False
