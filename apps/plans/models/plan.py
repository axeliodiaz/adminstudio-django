from mongoengine import (
    StringField,
    FloatField,
    IntField,
    BooleanField,
    ListField,
    ReferenceField,
)
from apps.plans.models.benefit import Benefit
from apps.plans.constants import PLAN_TYPE_MEMBERSHIP, PLAN_TYPE_PACKAGE
from apps.plans.models.mixins import UUIDModel, TimeStampedModel, SoftDeletableModel

from mongoengine import Document, StringField, BooleanField


class Plan(UUIDModel, TimeStampedModel, SoftDeletableModel):
    """
    Plan document stored in MongoDB using MongoEngine.
    Represents either a membership or a package.
    """

    TYPE_CHOICES = (PLAN_TYPE_MEMBERSHIP, PLAN_TYPE_PACKAGE)

    name = StringField(required=True, max_length=100)
    type = StringField(required=True, choices=TYPE_CHOICES)
    price = FloatField(required=True)
    duration_days = IntField(null=True)
    classes_included = IntField(null=True)

    benefits = ListField(ReferenceField(Benefit))

    is_active = BooleanField(default=True)

    meta = {
        "collection": "plans",
        "ordering": ["-created_at"],
        "indexes": ["name", "type", "is_active"],
    }

    def __str__(self) -> str:
        return f"{self.name} ({self.type}) - ${self.price}"
