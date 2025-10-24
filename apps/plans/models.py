from django.db import models
from model_utils.models import SoftDeletableModel, UUIDModel, TimeStampedModel

from apps.plans import constants


class Benefit(SoftDeletableModel, UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}"


class Plan(UUIDModel, TimeStampedModel, SoftDeletableModel):
    """
    Plan document stored in MongoDB using MongoEngine.
    Represents either a membership or a package.
    """

    TYPE_CHOICES = (
        (constants.PLAN_TYPE_MEMBERSHIP, "Membership"),
        (constants.PLAN_TYPE_PACKAGE, "Package"),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(
        max_length=100, choices=TYPE_CHOICES, default=constants.PLAN_TYPE_MEMBERSHIP
    )
    price = models.FloatField()
    duration_days = models.IntegerField(null=True)
    classes_included = models.IntegerField(null=True)

    is_active = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    is_highlighted = models.BooleanField(default=False)

    benefits = models.ManyToManyField("Benefit", related_name="plans", blank=True)
