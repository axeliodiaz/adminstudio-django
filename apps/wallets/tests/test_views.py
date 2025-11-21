"""Tests for apps.wallets.views."""

import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from drf_expiring_token.models import ExpiringToken

from apps.plans.models import Benefit, Plan
from apps.wallets.models import PlanPurchase, Wallet

User = get_user_model()


@pytest.mark.django_db
class TestWalletViewSetActivatePurchase:
    def test_activate_purchase_success(self, api_client, user, plan):
        """Test successful activation of a purchase."""
        # Create a purchase
        purchase = PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        # Authenticate
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        # Act
        url = reverse("wallet-activate-purchase")
        response = api_client.post(url, {"purchase_id": str(purchase.id)}, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        assert "wallet_id" in response.data
        assert "purchase_id" in response.data
        assert response.data["purchase_id"] == str(purchase.id)

        # Verify purchase was activated
        purchase.refresh_from_db()
        assert purchase.activated_since is not None

        # Verify wallet was created/updated
        wallet = Wallet.objects.get(user=user)
        assert wallet is not None

    def test_activate_purchase_already_activated(self, api_client, user, activated_plan_purchase):
        """Test that activating an already activated purchase returns 400."""
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-activate-purchase")
        response = api_client.post(
            url, {"purchase_id": str(activated_plan_purchase.id)}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_activate_purchase_not_found(self, api_client, user):
        """Test that activating a non-existent purchase returns 404."""
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-activate-purchase")
        fake_id = uuid.uuid4()
        response = api_client.post(url, {"purchase_id": str(fake_id)}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_activate_purchase_invalid_serializer(self, api_client, user):
        """Test that invalid serializer data returns 400."""
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-activate-purchase")
        response = api_client.post(url, {"purchase_id": "invalid-uuid"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_activate_purchase_missing_purchase_id(self, api_client, user):
        """Test that missing purchase_id returns 400."""
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-activate-purchase")
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestWalletViewSetList:
    def test_list_wallet_authenticated_user(self, api_client, user, wallet):
        """Test that authenticated user can view their own wallet."""
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "wallet" in response.data
        assert "purchases" in response.data
        # Handle UUID comparison (response.data may return UUID objects)
        wallet_id = response.data["wallet"]["id"]
        assert (str(wallet_id) == str(wallet.id)) or (wallet_id == wallet.id)
        assert response.data["wallet"]["class_credits"] == wallet.class_credits

    def test_list_wallet_creates_wallet_if_not_exists(self, api_client, user):
        """Test that wallet is created if it doesn't exist."""
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "wallet" in response.data
        # Verify wallet was created
        assert Wallet.objects.filter(user=user).exists()

    def test_list_wallet_unauthenticated(self, api_client):
        """Test that unauthenticated user gets 401."""
        url = reverse("wallet-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.data

    def test_list_wallet_with_purchases(self, api_client, user, wallet, plan):
        """Test that wallet list includes purchase history."""
        # Create some purchases
        purchase1 = PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )
        purchase2 = PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=Decimal("149.99"),
            activated_since=None,
        )

        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["purchases"]) == 2
        purchase_ids = {
            str(p["id"]) if isinstance(p["id"], uuid.UUID) else p["id"]
            for p in response.data["purchases"]
        }
        assert str(purchase1.id) in purchase_ids
        assert str(purchase2.id) in purchase_ids

    def test_list_wallet_staff_can_view_other_user(self, api_client, user, wallet):
        """Test that staff can view other users' wallets."""
        # Create a staff user
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass",
            is_staff=True,
        )

        token = Token.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        response = api_client.get(url, {"user_id": str(user.id)})

        assert response.status_code == status.HTTP_200_OK
        wallet_id = response.data["wallet"]["id"]
        assert (str(wallet_id) == str(wallet.id)) or (wallet_id == wallet.id)

    def test_list_wallet_superuser_can_view_other_user(self, api_client, user, wallet):
        """Test that superuser can view other users' wallets."""
        # Create a superuser
        superuser = User.objects.create_user(
            username="super",
            email="super@example.com",
            password="pass",
            is_superuser=True,
        )

        token = Token.objects.create(user=superuser)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        response = api_client.get(url, {"user_id": str(user.id)})

        assert response.status_code == status.HTTP_200_OK
        wallet_id = response.data["wallet"]["id"]
        assert (str(wallet_id) == str(wallet.id)) or (wallet_id == wallet.id)

    def test_list_wallet_non_staff_cannot_view_other_user(self, api_client, user, wallet):
        """Test that non-staff user cannot view other users' wallets."""
        # Create another regular user
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass",
        )

        token = Token.objects.create(user=other_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        response = api_client.get(url, {"user_id": str(user.id)})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in response.data["detail"].lower()

    def test_list_wallet_invalid_user_id(self, api_client, user):
        """Test that invalid user_id returns 400."""
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        response = api_client.get(url, {"user_id": "invalid-uuid"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_wallet_user_not_found(self, api_client, user):
        """Test that non-existent user_id returns 404."""
        # Create a staff user to have permission to query other users
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass",
            is_staff=True,
        )
        token = Token.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        fake_id = uuid.uuid4()
        response = api_client.get(url, {"user_id": str(fake_id)})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_wallet_purchases_ordered_by_most_recent(self, api_client, user, wallet, plan):
        """Test that purchases are ordered by most recent first."""
        from django.utils import timezone
        from datetime import timedelta

        # Create purchases at different times
        old_purchase = PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )
        # Manually set created time to be older
        PlanPurchase.objects.filter(id=old_purchase.id).update(
            created=timezone.now() - timedelta(days=2)
        )

        new_purchase = PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=Decimal("149.99"),
            activated_since=None,
        )

        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        purchases = response.data["purchases"]
        assert len(purchases) == 2
        # Most recent should be first
        # Handle UUID comparison
        first_id = purchases[0]["id"]
        second_id = purchases[1]["id"]
        assert (str(first_id) == str(new_purchase.id)) or (first_id == new_purchase.id)
        assert (str(second_id) == str(old_purchase.id)) or (second_id == old_purchase.id)

    def test_list_wallet_includes_plan_name(self, api_client, user, wallet, plan):
        """Test that purchase data includes plan name."""
        purchase = PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = reverse("wallet-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        purchase_data = response.data["purchases"][0]
        assert "plan_name" in purchase_data
        assert purchase_data["plan_name"] == plan.name
        # Handle UUID comparison
        plan_id = purchase_data["plan_id"]
        assert (str(plan_id) == str(plan.id)) or (plan_id == plan.id)
