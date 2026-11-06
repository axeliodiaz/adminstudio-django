"""Services for wallets app.

Encapsulate wallet activation logic for plan purchases.
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.wallets.constants import BenefitName, WalletField
from apps.wallets.exceptions import (
    InsufficientCreditsException,
    PurchaseAlreadyActivatedException,
)
from apps.wallets.models import ClassCreditLot, GiftCard, GuestPassInvitation, PlanPurchase, Wallet


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
    @transaction.atomic
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
        original_purchase = purchase
        purchase = (
            PlanPurchase.objects.select_for_update()
            .select_related("plan", "user")
            .get(pk=purchase.pk)
        )
        if purchase.activated_since:
            raise PurchaseAlreadyActivatedException(f"Purchase {purchase.id} is already activated")

        plan = purchase.plan
        user = purchase.user
        quantity = purchase.quantity or 1
        guest_passes_included = plan.guest_passes_included

        # 1. Get or create the user's Wallet
        wallet, created = Wallet.objects.select_for_update().get_or_create(user=user)

        # 2. Add classes_included to class_credits
        if plan.classes_included is not None:
            wallet.class_credits += plan.classes_included * quantity

        # 3. Add guest passes according to the plan configuration
        if guest_passes_included is not None:
            wallet.guest_pass_credits += guest_passes_included * quantity

        # 4. Extend active_membership_end_date by duration_days
        if plan.duration_days is not None:
            today = timezone.localdate()
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
        purchase.activated_since = timezone.localdate()
        # start and end will be automatically included in update_fields by the save method
        purchase.save(update_fields=["activated_since", "modified"])

        if plan.classes_included is not None and purchase.credit_expiry_enabled:
            ClassCreditLot.objects.create(
                wallet=wallet,
                purchase=purchase,
                initial_credits=plan.classes_included * quantity,
                remaining=plan.classes_included * quantity,
                expires_at=purchase.end,
            )
        # 7. Save the Wallet
        wallet.save()

        from apps.referrals.services import reward_first_purchase
        from apps.wallets.notifications import send_purchase_receipt_email

        has_previous_activated_purchase = (
            PlanPurchase.objects.filter(user=user, activated_since__isnull=False)
            .exclude(id=purchase.id)
            .exists()
        )
        if not has_previous_activated_purchase:
            reward_first_purchase(user=user)
        send_purchase_receipt_email(purchase)
        original_purchase.refresh_from_db()
        return wallet

    @staticmethod
    def consume_class_credit(user, *, class_time=None, reservation=None) -> bool:
        """Earliest eligible lot first, then grandfathered credits; class-time expiry."""
        when = class_time or timezone.now()
        with transaction.atomic():
            wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
            if wallet.is_unlimited_membership_active:
                if (
                    wallet.active_membership_end_date is None
                    or wallet.active_membership_end_date >= timezone.localtime(when).date()
                ):
                    return False
            lots = list(
                ClassCreditLot.objects.select_for_update()
                .filter(wallet=wallet, remaining__gt=0)
                .order_by(F("expires_at").asc(nulls_last=True), "created", "id")
            )
            eligible = next(
                (lot for lot in lots if lot.expires_at is None or lot.expires_at >= when), None
            )
            legacy = wallet.class_credits - sum(lot.remaining for lot in lots)
            if eligible is None and legacy <= 0:
                raise InsufficientCreditsException(
                    "No tienes créditos válidos para la fecha de esta clase. Compra un plan para reservar."
                )
            if eligible:
                if reservation is None:
                    raise ValueError(
                        "A reservation is required to preserve package credit provenance"
                    )
                eligible.remaining -= 1
                eligible.save(update_fields=["remaining", "modified"])
                reservation.credit_lot = eligible
            wallet.class_credits -= 1
            wallet.save(update_fields=["class_credits", "modified"])
            return True

    @staticmethod
    def refund_class_credit(user, *, reservation=None, studio_cancelled=False) -> None:
        """Restore only the charged origin, without extending a member's expiry."""
        with transaction.atomic():
            wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
            lot_id = reservation.credit_lot_id if reservation else None
            if lot_id:
                lot = ClassCreditLot.objects.select_for_update().get(pk=lot_id, wallet=wallet)
                if studio_cancelled and lot.expires_at and lot.expires_at < timezone.now():
                    # Owner policy: one separate non-expiring credit per refunded booking.
                    replacement, created = ClassCreditLot.objects.get_or_create(
                        replacement_for=reservation,
                        defaults={
                            "wallet": wallet,
                            "initial_credits": 1,
                            "remaining": 1,
                            "expires_at": None,
                        },
                    )
                    if not created:
                        return
                else:
                    lot.remaining += 1
                    lot.save(update_fields=["remaining", "modified"])
            # Old reservations already record whether a credit was charged. Do not
            # suppress their refund just because a newer unlimited plan is active.
            wallet.class_credits += 1
            wallet.save(update_fields=["class_credits", "modified"])

    @staticmethod
    def consume_guest_pass_credit(user) -> None:
        """Atomically debit one guest-pass credit when the guest books."""
        with transaction.atomic():
            wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
            if wallet.guest_pass_credits <= 0:
                raise InsufficientCreditsException("No te quedan pases de invitado.")
            wallet.guest_pass_credits -= 1
            wallet.save(update_fields=["guest_pass_credits", "modified"])

    @staticmethod
    def refund_guest_pass_credit(user) -> None:
        """Return one previously consumed guest-pass credit to its issuer."""
        with transaction.atomic():
            wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
            wallet.guest_pass_credits += 1
            wallet.save(update_fields=["guest_pass_credits", "modified"])

    @staticmethod
    def expire_guest_passes() -> int:
        """Mark unclaimed invitations past their expiry as expired."""
        return GuestPassInvitation.objects.filter(
            status__in=[GuestPassInvitation.Status.ISSUED, GuestPassInvitation.Status.CLAIMED],
            expires_at__lte=timezone.now(),
        ).update(status=GuestPassInvitation.Status.EXPIRED)

    @staticmethod
    def redeem_gift_card(*, user, code: str) -> GiftCard:
        """Atomically redeem a gift code into the authenticated user's wallet."""
        normalized_code = (code or "").strip().upper()
        if not normalized_code:
            raise ValueError("Debes ingresar un código de regalo.")

        with transaction.atomic():
            try:
                gift_card = (
                    GiftCard.objects.select_for_update()
                    .select_related("plan", "purchase")
                    .get(code=normalized_code)
                )
            except GiftCard.DoesNotExist as exc:
                raise ValueError("El código de regalo no es válido.") from exc

            now = timezone.now()
            if gift_card.status == GiftCard.Status.REDEEMED:
                raise ValueError("Este código de regalo ya fue canjeado.")
            if gift_card.status == GiftCard.Status.CANCELLED:
                raise ValueError("Este código de regalo fue cancelado.")
            if gift_card.expires_at <= now:
                if gift_card.status != GiftCard.Status.EXPIRED:
                    gift_card.status = GiftCard.Status.EXPIRED
                    gift_card.save(update_fields=["status", "modified"])
                raise ValueError("Este código de regalo está vencido.")
            if gift_card.status != GiftCard.Status.ACTIVE:
                raise ValueError("Este código de regalo no está disponible.")
            if gift_card.issuer_id == user.id:
                raise ValueError("No puedes canjear un regalo que emitiste.")

            redemption_purchase = PlanPurchase.objects.create(
                user=user,
                plan=gift_card.plan,
                quantity=1,
                price_paid=0,
                discount_amount=0,
                payment_method="gift_card",
                activated_since=None,
            )
            WalletService.activate_purchase(redemption_purchase)
            gift_card.status = GiftCard.Status.REDEEMED
            gift_card.redeemed_by = user
            gift_card.redeemed_at = now
            gift_card.redemption_purchase = redemption_purchase
            gift_card.save(
                update_fields=[
                    "status",
                    "redeemed_by",
                    "redeemed_at",
                    "redemption_purchase",
                    "modified",
                ]
            )
        return gift_card
