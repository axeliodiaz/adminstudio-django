"""API tests for promotional codes and checkout."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.plans import constants
from apps.plans.models import Plan, PromoCode
from apps.wallets.models import GiftCard, PlanPurchase, Wallet

User = get_user_model()


@pytest.fixture
def member_client(api_client):
    user = User.objects.create_user(
        username="member",
        email="member@example.com",
        password="pass1234",
    )
    token = ExpiringToken.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    api_client.user = user
    return api_client


@pytest.fixture
def staff_client(api_client):
    user = User.objects.create_user(
        username="adminuser",
        email="admin@example.com",
        password="pass1234",
        is_staff=True,
    )
    token = ExpiringToken.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def active_plan():
    return Plan.objects.create(
        name="Demo Estudiante",
        type=constants.PLAN_TYPE_MEMBERSHIP,
        price=39000,
        duration_days=30,
        classes_included=8,
        is_active=True,
    )


def _make_promo(**overrides):
    now = timezone.now()
    defaults = {
        "code": "VERANO10",
        "description": "10% off",
        "is_active": True,
        "valid_from": now - timedelta(days=1),
        "valid_until": now + timedelta(days=10),
        "discount_type": constants.DISCOUNT_TYPE_PERCENT,
        "discount_value": Decimal("10.00"),
    }
    defaults.update(overrides)
    return PromoCode.objects.create(**defaults)


@pytest.mark.django_db
class TestValidatePromoCode:
    def test_valid_code_returns_discount(self, api_client, active_plan):
        _make_promo()
        response = api_client.post(
            reverse("plan-validate-promo"),
            {"code": "verano10", "plan_id": str(active_plan.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == "VERANO10"
        assert response.data["discount_amount"] == 3900.0
        assert response.data["total"] == 35100.0

    def test_inactive_code_is_rejected(self, api_client):
        _make_promo(is_active=False)
        response = api_client.post(
            reverse("plan-validate-promo"),
            {"code": "VERANO10"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "activo" in response.data["detail"].lower()

    def test_expired_code_is_rejected(self, api_client):
        now = timezone.now()
        _make_promo(valid_from=now - timedelta(days=10), valid_until=now - timedelta(days=1))
        response = api_client.post(
            reverse("plan-validate-promo"),
            {"code": "VERANO10"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rango" in response.data["detail"].lower()

    def test_future_code_is_rejected(self, api_client):
        now = timezone.now()
        _make_promo(valid_from=now + timedelta(days=1), valid_until=now + timedelta(days=10))
        response = api_client.post(
            reverse("plan-validate-promo"),
            {"code": "VERANO10"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCheckout:
    def test_checkout_applies_promo_and_quantity(self, member_client, active_plan, mocker):
        mocker.patch("apps.wallets.notifications.send_purchase_receipt_email")
        _make_promo()
        response = member_client.post(
            reverse("plan-checkout"),
            {
                "items": [{"plan_id": str(active_plan.id), "quantity": 2}],
                "promo_code": "VERANO10",
                "payment_method": "webpay",
                "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["subtotal"] == 78000.0
        assert response.data["discount"] == 7800.0
        assert response.data["total"] == 70200.0
        purchase = PlanPurchase.objects.get()
        assert purchase.quantity == 2
        assert purchase.payment_method == "webpay"
        assert purchase.promo_code.code == "VERANO10"
        assert purchase.price_paid == Decimal("70200.00")
        assert purchase.activated_since is not None

    def test_checkout_requires_terms(self, member_client, active_plan):
        response = member_client.post(
            reverse("plan-checkout"),
            {
                "items": [{"plan_id": str(active_plan.id), "quantity": 1}],
                "payment_method": "mercadopago",
                "accept_terms": False,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_purchase_accepts_promo_code(self, member_client, active_plan, mocker):
        mocker.patch("apps.wallets.notifications.send_purchase_receipt_email")
        _make_promo(discount_type=constants.DISCOUNT_TYPE_FIXED, discount_value=Decimal("4000"))
        response = member_client.post(
            reverse("plan-purchase"),
            {
                "plan_id": str(active_plan.id),
                "promo_code": "VERANO10",
                "payment_method": "mercadopago",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        purchase = PlanPurchase.objects.get()
        assert purchase.price_paid == Decimal("35000.00")
        assert purchase.activated_since is not None

    def test_checkout_leaves_purchase_pending_when_psp_enabled(
        self, member_client, active_plan, settings, mocker
    ):
        settings.ENABLE_PSP_PAYMENTS = True
        send_email = mocker.patch("apps.wallets.notifications.send_purchase_receipt_email")
        response = member_client.post(
            reverse("plan-checkout"),
            {
                "items": [{"plan_id": str(active_plan.id), "quantity": 1}],
                "payment_method": "webpay",
                "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        purchase = PlanPurchase.objects.get()
        assert purchase.activated_since is None
        send_email.assert_not_called()

    def test_checkout_activates_wallet_and_sends_receipt(self, member_client, active_plan, mocker):
        send_email = mocker.patch("apps.wallets.notifications.send_purchase_receipt_email")
        response = member_client.post(
            reverse("plan-checkout"),
            {
                "items": [{"plan_id": str(active_plan.id), "quantity": 1}],
                "payment_method": "webpay",
                "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        purchase = PlanPurchase.objects.get()
        assert purchase.activated_since is not None
        send_email.assert_called_once()
        from apps.wallets.models import Wallet

        wallet = Wallet.objects.get(user=member_client.user)
        assert wallet.class_credits == active_plan.classes_included

    def test_checkout_issues_one_gift_per_item_and_does_not_credit_issuer(
        self, member_client, active_plan, mocker
    ):
        send_gift = mocker.patch("apps.plans.checkout_services.send_gift_recipient_email")
        response = member_client.post(
            reverse("plan-checkout"),
            {
                "items": [{"plan_id": str(active_plan.id), "quantity": 2}],
                "payment_method": "webpay",
                "accept_terms": True,
                "gift_recipient": {
                    "name": "Regalo Rider",
                    "email": "gift@example.com",
                    "message": "Disfruta tu ride",
                },
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data["gifts"]) == 2
        assert GiftCard.objects.filter(status=GiftCard.Status.ACTIVE).count() == 2
        assert not Wallet.objects.filter(user=member_client.user).exists()
        send_gift.assert_called()


@pytest.mark.django_db
class TestGiftCardRedemption:
    def test_member_can_redeem_a_gift_only_once(self, member_client, active_plan, mocker):
        mocker.patch("apps.plans.checkout_services.send_gift_recipient_email")
        mocker.patch("apps.wallets.notifications.send_purchase_receipt_email")
        checkout = member_client.post(
            reverse("plan-checkout"),
            {
                "items": [{"plan_id": str(active_plan.id), "quantity": 1}],
                "accept_terms": True,
                "gift_recipient": {"email": "gift@example.com"},
            },
            format="json",
        )
        code = checkout.data["gifts"][0]["code"]
        recipient = User.objects.create_user(
            username="recipient", email="recipient@example.com", password="pass1234"
        )
        token = ExpiringToken.objects.create(user=recipient)
        member_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = member_client.post(reverse("gift-card-redeem"), {"code": code}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == GiftCard.Status.REDEEMED
        assert Wallet.objects.get(user=recipient).class_credits == active_plan.classes_included

        second_response = member_client.post(
            reverse("gift-card-redeem"), {"code": code}, format="json"
        )
        assert second_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya fue canjeado" in second_response.data["detail"]


@pytest.mark.django_db
class TestAdminPromoCodes:
    def test_staff_can_create_and_update(self, staff_client):
        now = timezone.now()
        create_response = staff_client.post(
            reverse("admin-promo-list"),
            {
                "code": "staff20",
                "description": "Staff perk",
                "is_active": True,
                "valid_from": (now - timedelta(days=1)).isoformat(),
                "valid_until": (now + timedelta(days=30)).isoformat(),
                "discount_type": "PERCENT",
                "discount_value": 20,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        assert create_response.data["code"] == "STAFF20"
        promo_id = create_response.data["id"]

        update_response = staff_client.patch(
            reverse("admin-promo-detail", kwargs={"promo_id": promo_id}),
            {"is_active": False},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["is_active"] is False

    def test_member_cannot_list(self, member_client):
        response = member_client.get(reverse("admin-promo-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN
