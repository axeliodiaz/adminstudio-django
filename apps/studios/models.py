from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class Studio(SoftDeletableModel, UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)

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
