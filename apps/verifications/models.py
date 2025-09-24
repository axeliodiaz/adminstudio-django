from django.conf import settings
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel

from apps.verifications import constants


class VerificationCode(SoftDeletableModel, UUIDModel, TimeStampedModel):
    code = models.CharField(max_length=constants.VERIFICATION_CODE_SIZE, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_codes"
    )
    has_confirmed = models.BooleanField()
    expires_at = models.DateTimeField()
