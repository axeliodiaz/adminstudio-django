from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.plans.models import Plan
from apps.referrals.models import Referral, ReferralProgramSettings
from apps.referrals.services import (
    attribute_signup,
    get_or_create_referral_code,
    reward_first_purchase,
)
from apps.wallets.models import PlanPurchase, Wallet
from apps.wallets.services import WalletService

User = get_user_model()


@pytest.mark.django_db
class TestReferralServices:
    def test_rewards_both_users_once(self, user):
        referred = User.objects.create_user(
            username="referred",
            email="referred@example.com",
            password="password",
        )
        code = get_or_create_referral_code(user=user)
        referral = attribute_signup(referred_user=referred, code=code.code)

        reward_first_purchase(user=referred)
        reward_first_purchase(user=referred)

        referral.refresh_from_db()
        assert referral.rewarded_at is not None
        assert referral.referrer_credits_awarded == 1
        assert referral.referred_credits_awarded == 1
        assert Wallet.objects.get(user=user).class_credits == 1
        assert Wallet.objects.get(user=referred).class_credits == 1

    def test_rejects_self_referral(self, user):
        code = get_or_create_referral_code(user=user)

        with pytest.raises(ValueError, match="propio"):
            attribute_signup(referred_user=user, code=code.code)

    def test_monthly_limit_does_not_reward_referrer(self, user):
        ReferralProgramSettings.objects.create(monthly_referrer_reward_limit=1)
        code = get_or_create_referral_code(user=user)
        first = User.objects.create_user(
            username="first", email="first@example.com", password="password"
        )
        second = User.objects.create_user(
            username="second", email="second@example.com", password="password"
        )
        attribute_signup(referred_user=first, code=code.code)
        second_referral = attribute_signup(referred_user=second, code=code.code)

        reward_first_purchase(user=first)
        reward_first_purchase(user=second)

        second_referral.refresh_from_db()
        assert second_referral.converted_at is not None
        assert second_referral.rewarded_at is None
        assert Wallet.objects.get(user=user).class_credits == 1

    def test_wallet_activation_only_rewards_on_first_purchase(self, user):
        referred = User.objects.create_user(
            username="first-purchase",
            email="first-purchase@example.com",
            password="password",
        )
        code = get_or_create_referral_code(user=user)
        referral = attribute_signup(referred_user=referred, code=code.code)
        plan = Plan.objects.create(
            name="Pack",
            type="PACKAGE",
            price=Decimal("100.00"),
            classes_included=1,
            is_active=True,
        )
        first_purchase = PlanPurchase.objects.create(
            user=referred, plan=plan, price_paid=Decimal("100.00")
        )
        second_purchase = PlanPurchase.objects.create(
            user=referred, plan=plan, price_paid=Decimal("100.00")
        )

        WalletService.activate_purchase(first_purchase)
        WalletService.activate_purchase(second_purchase)

        referral.refresh_from_db()
        assert referral.rewarded_at is not None
        assert Wallet.objects.get(user=user).class_credits == 1
