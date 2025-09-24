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
