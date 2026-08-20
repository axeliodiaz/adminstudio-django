"""API tests for staff admin wallet endpoints."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from drf_expiring_token.models import ExpiringToken
from model_bakery import baker

from apps.wallets.models import PlanPurchase, Wallet

User = get_user_model()


@pytest.fixture
def staff_client(api_client):
    staff_user = User.objects.create_user(
        username="walletadmin",
        email="walletadmin@example.com",
        password="testpass123",
        is_staff=True,
    )
    token = ExpiringToken.objects.create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestAdminWalletListView:
    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse("admin-wallet-list"))
        assert response.status_code == 401

    def test_returns_wallets_for_staff(self, staff_client):
        user = User.objects.create_user(
            username="socio.wallet",
            email="socio.wallet@example.com",
            password="pass1234",
            first_name="María",
            last_name="González",
        )
        Wallet.objects.create(
            user=user,
            class_credits=6,
            guest_pass_credits=2,
            active_membership_end_date=timezone.localdate(),
            is_priority_booker=True,
        )
        plan = baker.make("plans.Plan", name="Starter 8", type="PACKAGE")
        PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=69000,
            activated_since=timezone.localdate(),
        )

        response = staff_client.get(reverse("admin-wallet-list"))
        assert response.status_code == 200
        match = next(
            row for row in response.data if row["user_email"] == "socio.wallet@example.com"
        )
        assert match["user_name"] == "María González"
        assert match["class_credits"] == 6
        assert match["guest_pass_credits"] == 2
        assert match["is_priority"] is True
        assert match["plan_name"] == "Starter 8"


@pytest.mark.django_db
class TestAdminPurchaseListView:
    def test_returns_purchases_for_staff(self, staff_client):
        user = User.objects.create_user(
            username="buyer",
            email="buyer@example.com",
            password="pass1234",
            first_name="Pedro",
            last_name="Silva",
        )
        plan = baker.make("plans.Plan", name="Unlimited", type="MEMBERSHIP", price=120000)
        PlanPurchase.objects.create(
            user=user, plan=plan, price_paid=120000, activated_since=timezone.localdate()
        )

        response = staff_client.get(reverse("admin-purchase-list"))
        assert response.status_code == 200
        assert any(
            row["user_name"] == "Pedro Silva" and row["plan_name"] == "Unlimited"
            for row in response.data
        )
