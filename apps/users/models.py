from django.contrib.auth.models import AbstractUser
from django.db import models
from model_utils import Choices
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class User(AbstractUser, SoftDeletableModel, UUIDModel, TimeStampedModel):
    GENDER = Choices(
        ("female", "Female"),
        ("male", "Male"),
        ("other", "Other"),
    )

    phone_number = models.CharField(max_length=30, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER, default=GENDER.other, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    # Profile-related fields (migrated from Profile model)
    height_cm = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Height in centimeters.",
    )
    weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight in kilograms.",
    )
    shoe_size = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Shoe size (e.g. 40.5).",
    )
    # Cycling-related fields
    seat_height = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Seat height in centimeters.",
    )
    seat_distance = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Seat distance in centimeters.",
    )
    handlebar_distance = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Handlebar distance in centimeters.",
    )
    cycling_shoe_size = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Cycling shoe size (e.g. 44.0).",
    )
