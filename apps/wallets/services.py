"""Services for wallets app.

Encapsulate wallet activation logic for plan purchases.
"""

from datetime import timedelta

from django.utils import timezone

from apps.wallets.constants import BenefitName, WalletField
from apps.wallets.exceptions import PurchaseAlreadyActivatedException
from apps.wallets.models import PlanPurchase, Wallet


class WalletService:
    """
    Service class for wallet operations.
    Handles activation of plan purchases and wallet updates.
    """

    # Mapping of benefit names to Wallet fields
    # Uses case-insensitive comparison for greater flexibility
    BENEFIT_TO_WALLET_FIELD = {
        BenefitName.PRIORITY_BOOKING: WalletField.IS_PRIORITY_BOOKER,
        BenefitName.PRIORITY_BOOKER: WalletField.IS_PRIORITY_BOOKER,
        BenefitName.RESERVA_PRIORITARIA: WalletField.IS_PRIORITY_BOOKER,
        BenefitName.FREEZE_MEMBERSHIP: WalletField.CAN_FREEZE_MEMBERSHIP,
        BenefitName.CONGELAR_MEMBRESIA: WalletField.CAN_FREEZE_MEMBERSHIP,
        BenefitName.CAN_FREEZE: WalletField.CAN_FREEZE_MEMBERSHIP,
        BenefitName.FOUNDERS_EXCLUSIVE: WalletField.IS_FOUNDERS_EXCLUSIVE,
        BenefitName.FOUNDERS_PASS: WalletField.IS_FOUNDERS_EXCLUSIVE,
        BenefitName.FOUNDERS: WalletField.IS_FOUNDERS_EXCLUSIVE,
        BenefitName.UNLIMITED_MEMBERSHIP: WalletField.IS_UNLIMITED_MEMBERSHIP_ACTIVE,
        BenefitName.MEMBRESIA_ILIMITADA: WalletField.IS_UNLIMITED_MEMBERSHIP_ACTIVE,
        BenefitName.UNLIMITED: WalletField.IS_UNLIMITED_MEMBERSHIP_ACTIVE,
    }

    @staticmethod
    def activate_purchase(purchase: PlanPurchase) -> Wallet:
        """
        Activates a plan purchase and updates the user's Wallet.

        This method should be called after a successful purchase to:
        1. Get or create the user's Wallet
        2. Add classes_included to class_credits
        3. Add guest passes (hardcoded to 1 for now)
        4. Extend active_membership_end_date by duration_days
        5. Update boolean flags according to the plan's benefits
        6. Mark the purchase as activated

        Args:
            purchase: PlanPurchase instance to activate

        Returns:
            Wallet: The updated Wallet instance

        Raises:
            PurchaseAlreadyActivatedException: If the purchase is already activated
        """
        if purchase.activated_since:
            raise PurchaseAlreadyActivatedException(f"Purchase {purchase.id} is already activated")

        plan = purchase.plan
        user = purchase.user
        quantity = purchase.quantity or 1
        guest_passes_included = plan.guest_passes_included

        # 1. Get or create the user's Wallet
        wallet, created = Wallet.objects.get_or_create(user=user)

        # 2. Add classes_included to class_credits
        if plan.classes_included is not None:
            wallet.class_credits += plan.classes_included * quantity

        # 3. Add guest passes according to the plan configuration
        if guest_passes_included is not None:
            wallet.guest_pass_credits += guest_passes_included * quantity

        # 4. Extend active_membership_end_date by duration_days
        if plan.duration_days is not None:
            today = timezone.now().date()
            if wallet.active_membership_end_date:
                # If it already has an expiration date, extend from that date
                # or from today, whichever is more recent
                base_date = max(wallet.active_membership_end_date, today)
            else:
                # If it has no date, start from today
                base_date = today

            wallet.active_membership_end_date = base_date + timedelta(
                days=plan.duration_days * quantity
            )

        # 5. Iterate over the Plan's benefits to update boolean flags
        active_benefits = plan.benefits.filter(is_active=True)
        for benefit in active_benefits:
            benefit_name_lower = benefit.name.lower().strip()

            # Find the corresponding field in the mapping
            wallet_field = WalletService.BENEFIT_TO_WALLET_FIELD.get(benefit_name_lower)

            if wallet_field:
                setattr(wallet, wallet_field, True)

        # 6. Mark the purchase as activated and save
        # Ensure plan is loaded for start/end calculation
        if not purchase.plan:
            purchase.plan = plan
        purchase.activated_since = timezone.now().date()
        # start and end will be automatically included in update_fields by the save method
        purchase.save(update_fields=["activated_since", "modified"])

        # 7. Save the Wallet
        wallet.save()

        return wallet
