from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class Address(SoftDeletableModel, UUIDModel, TimeStampedModel):
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Latitude for this address.",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Longitude for this address.",
    )

    def __str__(self):
        return self.address


class Studio(SoftDeletableModel, UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=100)
    address = models.ForeignKey(
        "Address",
        on_delete=models.SET_NULL,
        related_name="studios",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=False)
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def rooms_list(self):
        """Return related rooms as a concrete list to ease Pydantic serialization."""
        return list(self.rooms.all())


class Room(SoftDeletableModel, UUIDModel, TimeStampedModel):
    studio = models.ForeignKey(
        Studio,
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name
