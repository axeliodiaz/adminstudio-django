# apps/wallet/models.py
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from model_utils.models import TimeFramedModel, TimeStampedModel, UUIDModel


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


class PlanPurchase(UUIDModel, TimeStampedModel, TimeFramedModel):
    """
    Immutable record of a Plan purchase by a User.
    Stores historical information of the purchase transaction.
    The start and end fields are calculated based on activated_since and plan.duration_days.
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
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Discount Amount",
    )
    promo_code = models.ForeignKey(
        "plans.PromoCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchases",
        verbose_name="Promo code",
    )
    payment_method = models.CharField(
        max_length=32,
        blank=True,
        verbose_name="Payment method",
    )
    activated_since = models.DateField(null=True, blank=True, verbose_name="Activated Since")

    class Meta:
        verbose_name = "Plan Purchase"
        verbose_name_plural = "Plan Purchases"
        ordering = ["-created"]

    def save(self, *args, **kwargs):
        """
        Calculate and set start and end fields based on activated_since and plan.duration_days.
        Automatically includes start and end in update_fields if they are calculated.
        """
        # Ensure plan is loaded if we need to calculate end and it's not already loaded
        if self.activated_since and self.plan_id and not self.plan:
            from apps.plans.models import Plan

            try:
                self.plan = Plan.objects.get(id=self.plan_id)
            except Plan.DoesNotExist:
                pass

        if self.activated_since:
            # Calculate start: beginning of the activation date
            self.start = timezone.make_aware(
                datetime.combine(self.activated_since, datetime.min.time())
            )
            # Calculate end: end of the day after duration_days
            if self.plan and self.plan.duration_days:
                end_date = self.activated_since + timedelta(days=self.plan.duration_days)
                self.end = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
            else:
                self.end = None
        else:
            self.start = None
            self.end = None

        # If update_fields is specified, include start and end if they were calculated
        update_fields = kwargs.get("update_fields", None)
        if update_fields is not None:
            update_fields = set(update_fields)
            if self.start is not None:
                update_fields.add("start")
            if self.end is not None:
                update_fields.add("end")
            kwargs["update_fields"] = list(update_fields)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Purchase of {self.plan.name} by {self.user.username} - ${self.price_paid}"
