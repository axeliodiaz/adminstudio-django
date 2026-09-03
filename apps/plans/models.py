from django.db import models
from model_utils.models import SoftDeletableModel, UUIDModel, TimeStampedModel

from apps.plans import constants


class Benefit(SoftDeletableModel, UUIDModel, TimeStampedModel):
    """
    Represents a Benefit entity with attributes and behaviors necessary for handling
    benefits within the application.

    This class serves as a model for storing benefits data. It includes attributes
    to define the name, description, and its active status. Inherits functionalities
    from SoftDeletableModel, UUIDModel, and TimeStampedModel.

    Attributes:
        name (str): The name of the benefit.
        description (str): A detailed description of the benefit.
        is_active (bool): Indicates whether the benefit is active.
    """

    name = models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}"


class Plan(UUIDModel, TimeStampedModel, SoftDeletableModel):
    """
    Represents a plan for a service or product with various attributes and options.

    This class defines a blueprint for creating and managing plans, including details
    like the name, type, price, duration, and associated benefits. Plans can be categorized
    and are configurable with indicators like popularity, activity status, and whether they
    are highlighted. It integrates additional functionality from the UUIDModel,
    TimeStampedModel, and SoftDeletableModel base models, such as unique identification,
    timestamps, and soft-deletion support.

    Attributes:
        name (str): The name of the plan.
        type (str): The type of the plan, chosen from predefined type choices.
        price (float): The price of the plan.
        duration_days (int or None): The number of days the plan is valid. Can be None if not applicable.
        classes_included (int or None): The number of classes included in the plan.
            Can be None if not applicable.
        guest_passes_included (int or None): The number of guest passes included in the plan.
            Can be None if not applicable.
        is_active (bool): Indicates whether the plan is currently active.
        is_popular (bool): Indicates whether the plan is marked as popular.
        is_highlighted (bool): Indicates whether the plan is highlighted.
        benefits (ManyToManyField): The benefits associated with the plan.
    """

    TYPE_CHOICES = (
        (constants.PLAN_TYPE_MEMBERSHIP, "Membership"),
        (constants.PLAN_TYPE_PACKAGE, "Package"),
        (constants.PLAN_TYPE_GIFT_CARD, "Gift card"),
        (constants.PLAN_TYPE_GIFT_PACK, "Gift pack"),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(
        max_length=100, choices=TYPE_CHOICES, default=constants.PLAN_TYPE_MEMBERSHIP
    )
    price = models.FloatField()
    duration_days = models.IntegerField(null=True)
    classes_included = models.IntegerField(null=True, blank=True)
    guest_passes_included = models.IntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    is_highlighted = models.BooleanField(default=False)
    is_first_timer = models.BooleanField(
        default=False,
        help_text="Available only to users who have never completed a plan purchase.",
    )

    benefits = models.ManyToManyField("Benefit", related_name="plans", blank=True)

    @property
    def benefits_list(self):
        return list(self.benefits.filter(is_active=True).order_by("name"))

    def __str__(self):
        return f"{self.name}"


class PromoCode(UUIDModel, TimeStampedModel, SoftDeletableModel):
    """Promotional discount code with an active flag and a validity window."""

    DISCOUNT_TYPE_CHOICES = (
        (constants.DISCOUNT_TYPE_PERCENT, "Percentage"),
        (constants.DISCOUNT_TYPE_FIXED, "Fixed amount"),
    )

    code = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    discount_type = models.CharField(
        max_length=16,
        choices=DISCOUNT_TYPE_CHOICES,
        default=constants.DISCOUNT_TYPE_PERCENT,
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Promo code"
        verbose_name_plural = "Promo codes"
        ordering = ["-created"]

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code
