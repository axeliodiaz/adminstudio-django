"""Tests for apps.wallets.services."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.plans.models import Benefit, Plan
from apps.wallets.exceptions import PurchaseAlreadyActivatedException
from apps.wallets.models import PlanPurchase, Wallet
from apps.wallets.services import WalletService


@pytest.fixture(autouse=True)
def mute_purchase_receipt_email(mocker):
    mocker.patch("apps.wallets.notifications.send_purchase_receipt_email")


class TestWalletServiceActivatePurchase:
    @pytest.mark.django_db
    def test_activates_purchase_and_creates_wallet(self, user, plan):
        """Test that activating a purchase creates a wallet if it doesn't exist."""
        purchase = PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        wallet = WalletService.activate_purchase(purchase)

        assert wallet is not None
        assert wallet.user == user
        purchase.refresh_from_db()
        assert purchase.activated_since is not None

    @pytest.mark.django_db
    def test_activates_purchase_and_updates_existing_wallet(self, wallet, plan):
        """Test that activating a purchase updates an existing wallet."""
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        initial_credits = wallet.class_credits
        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.class_credits == initial_credits + plan.classes_included

    @pytest.mark.django_db
    def test_adds_class_credits(self, wallet, plan):
        """Test that class credits are added to the wallet."""
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        initial_credits = wallet.class_credits
        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.class_credits == initial_credits + plan.classes_included

    @pytest.mark.django_db
    def test_adds_guest_pass_credits(self, wallet, plan):
        """Test that guest pass credits are added to the wallet."""
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        initial_guest_passes = wallet.guest_pass_credits
        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.guest_pass_credits == initial_guest_passes + plan.guest_passes_included

    @pytest.mark.django_db
    def test_handles_none_class_credits(self, wallet):
        """Test that None class_credits are handled correctly."""
        plan = Plan.objects.create(
            name="No Classes Plan",
            type="MEMBERSHIP",
            price=50.0,
            duration_days=30,
            classes_included=None,
            guest_passes_included=1,
            is_active=True,
        )
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("50.00"),
            activated_since=None,
        )

        initial_credits = wallet.class_credits
        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.class_credits == initial_credits  # Should not change

    @pytest.mark.django_db
    def test_handles_none_guest_passes(self, wallet):
        """Test that None guest_passes_included are handled correctly."""
        plan = Plan.objects.create(
            name="No Guest Passes Plan",
            type="MEMBERSHIP",
            price=50.0,
            duration_days=30,
            classes_included=5,
            guest_passes_included=None,
            is_active=True,
        )
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("50.00"),
            activated_since=None,
        )

        initial_guest_passes = wallet.guest_pass_credits
        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.guest_pass_credits == initial_guest_passes  # Should not change

    @pytest.mark.django_db
    def test_extends_membership_end_date_from_today(self, wallet, plan):
        """Test that membership end date is extended from today when wallet has no end date."""
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        today = timezone.now().date()
        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        expected_end_date = today + timedelta(days=plan.duration_days)
        assert wallet.active_membership_end_date == expected_end_date

    @pytest.mark.django_db
    def test_extends_membership_end_date_from_existing_date(self, wallet, plan):
        """Test that membership end date is extended from existing date if it's in the future."""
        future_date = timezone.now().date() + timedelta(days=10)
        wallet.active_membership_end_date = future_date
        wallet.save()

        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        expected_end_date = future_date + timedelta(days=plan.duration_days)
        assert wallet.active_membership_end_date == expected_end_date

    @pytest.mark.django_db
    def test_extends_membership_end_date_from_today_if_past(self, wallet, plan):
        """Test that membership end date is extended from today if existing date is in the past."""
        past_date = timezone.now().date() - timedelta(days=10)
        wallet.active_membership_end_date = past_date
        wallet.save()

        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        today = timezone.now().date()
        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        expected_end_date = today + timedelta(days=plan.duration_days)
        assert wallet.active_membership_end_date == expected_end_date

    @pytest.mark.django_db
    def test_handles_none_duration_days(self, wallet):
        """Test that None duration_days are handled correctly."""
        plan = Plan.objects.create(
            name="No Duration Plan",
            type="PACKAGE",
            price=50.0,
            duration_days=None,
            classes_included=5,
            guest_passes_included=1,
            is_active=True,
        )
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("50.00"),
            activated_since=None,
        )

        initial_end_date = wallet.active_membership_end_date
        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        # Should not change if duration_days is None
        assert wallet.active_membership_end_date == initial_end_date

    @pytest.mark.django_db
    def test_activates_priority_booking_benefit(self, wallet, plan, benefit_priority_booking):
        """Test that priority booking benefit is activated."""
        plan.benefits.set([benefit_priority_booking])
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.is_priority_booker is True

    @pytest.mark.django_db
    def test_activates_freeze_membership_benefit(self, wallet, plan, benefit_freeze_membership):
        """Test that freeze membership benefit is activated."""
        plan.benefits.set([benefit_freeze_membership])
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.can_freeze_membership is True

    @pytest.mark.django_db
    def test_activates_founders_exclusive_benefit(self, wallet, plan, benefit_founders_exclusive):
        """Test that founders exclusive benefit is activated."""
        plan.benefits.set([benefit_founders_exclusive])
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.is_founders_exclusive is True

    @pytest.mark.django_db
    def test_activates_unlimited_membership_benefit(
        self, wallet, plan, benefit_unlimited_membership
    ):
        """Test that unlimited membership benefit is activated."""
        plan.benefits.set([benefit_unlimited_membership])
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.is_unlimited_membership_active is True

    @pytest.mark.django_db
    def test_activates_multiple_benefits(
        self, wallet, plan, benefit_priority_booking, benefit_freeze_membership
    ):
        """Test that multiple benefits are activated."""
        plan.benefits.set([benefit_priority_booking, benefit_freeze_membership])
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.is_priority_booker is True
        assert wallet.can_freeze_membership is True

    @pytest.mark.django_db
    def test_ignores_inactive_benefits(self, wallet, plan):
        """Test that inactive benefits are ignored."""
        inactive_benefit = Benefit.objects.create(
            name="Priority Booking",
            description="Priority booking",
            is_active=False,
        )
        plan.benefits.set([inactive_benefit])
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.is_priority_booker is False

    @pytest.mark.django_db
    def test_benefit_name_case_insensitive(self, wallet, plan):
        """Test that benefit name matching is case-insensitive."""
        # Test with lowercase
        benefit = Benefit.objects.create(
            name="priority booking",
            description="Priority booking",
            is_active=True,
        )
        plan.benefits.set([benefit])
        purchase = PlanPurchase.objects.create(
            user=wallet.user,
            plan=plan,
            price_paid=Decimal("99.99"),
            activated_since=None,
        )

        WalletService.activate_purchase(purchase)

        wallet.refresh_from_db()
        assert wallet.is_priority_booker is True

    @pytest.mark.django_db
    def test_raises_exception_if_already_activated(self, activated_plan_purchase):
        """Test that activating an already activated purchase raises an exception."""
        with pytest.raises(PurchaseAlreadyActivatedException) as exc_info:
            WalletService.activate_purchase(activated_plan_purchase)

        assert str(activated_plan_purchase.id) in str(exc_info.value)

    @pytest.mark.django_db
    def test_sets_activated_since_date(self, plan_purchase):
        """Test that activated_since is set to today's date."""
        today = timezone.now().date()
        WalletService.activate_purchase(plan_purchase)

        plan_purchase.refresh_from_db()
        assert plan_purchase.activated_since == today

    @pytest.mark.django_db
    def test_calculates_start_and_end_dates(self, plan_purchase):
        """Test that start and end dates are calculated correctly."""
        WalletService.activate_purchase(plan_purchase)

        plan_purchase.refresh_from_db()
        assert plan_purchase.start is not None
        assert plan_purchase.end is not None
        assert plan_purchase.activated_since is not None

        # Check that end is after start
        assert plan_purchase.end > plan_purchase.start

        # Check that the duration matches plan.duration_days
        duration = plan_purchase.end.date() - plan_purchase.activated_since
        assert duration.days == plan_purchase.plan.duration_days
