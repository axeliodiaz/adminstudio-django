# apps/wallet/models.py
from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel, UUIDModel


class Wallet(UUIDModel, TimeStampedModel):
    """
    Represents a user's wallet or asset account.
    Stores consumable balances (classes, passes) and active benefits.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
        verbose_name="Owner User",
    )

    class_credits = models.IntegerField(default=0, verbose_name="Class Credits")
    guest_pass_credits = models.IntegerField(default=0, verbose_name="Guest Pass Credits")

    # --- MEMBERSHIP STATUS AND BENEFITS ---
    # The date until which the current membership (by duration) is valid.
    active_membership_end_date = models.DateField(
        null=True, blank=True, verbose_name="Active Membership End Date"
    )

    # Stores the discount percentage applicable in retail.
    # (e.g., 0.10 for 10%). Updated when purchasing a Plan with a better %.
    retail_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0, verbose_name="Retail Discount (%)"
    )

    # Boolean flags for non-consumable benefits that remain active.
    # Activated if the purchased Plan includes the Benefit.
    is_priority_booker = models.BooleanField(default=False, verbose_name="Priority Booking Active")
    can_freeze_membership = models.BooleanField(
        default=False, verbose_name="Freeze Membership Option"
    )
    is_founders_exclusive = models.BooleanField(default=False, verbose_name="Founders Pass Benefit")

    # Recommended to maintain a record of active unlimited membership, if applicable.
    is_unlimited_membership_active = models.BooleanField(
        default=False, verbose_name="Unlimited Membership"
    )

    def __str__(self):
        return f"Wallet for {self.user.username}"


class PlanPurchase(UUIDModel, TimeStampedModel):
    """
    Immutable record of a Plan purchase by a User.
    Stores historical information of the purchase transaction.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="plan_purchases",
        verbose_name="User",
    )
    plan = models.ForeignKey(
        "plans.Plan",
        on_delete=models.PROTECT,
        related_name="purchases",
        verbose_name="Purchased Plan",
    )
    price_paid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price Paid")
    is_activated = models.BooleanField(default=False, verbose_name="Activated")

    class Meta:
        verbose_name = "Plan Purchase"
        verbose_name_plural = "Plan Purchases"
        ordering = ["-created"]

    def __str__(self):
        return f"Purchase of {self.plan.name} by {self.user.username} - ${self.price_paid}"
