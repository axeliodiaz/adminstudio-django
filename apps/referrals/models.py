from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel, UUIDModel


class ReferralProgramSettings(TimeStampedModel):
    """Singleton-like configuration managed through Django admin."""

    is_active = models.BooleanField(default=True)
    referrer_credit_reward = models.PositiveSmallIntegerField(default=1)
    referred_credit_reward = models.PositiveSmallIntegerField(default=1)
    monthly_referrer_reward_limit = models.PositiveSmallIntegerField(default=10)

    class Meta:
        verbose_name = "Referral program settings"
        verbose_name_plural = "Referral program settings"

    def __str__(self):
        return "Referral program settings"


class ReferralCode(UUIDModel, TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_code",
    )
    code = models.CharField(max_length=16, unique=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.code} ({self.user})"


class ReferralClick(UUIDModel, TimeStampedModel):
    referral_code = models.ForeignKey(
        ReferralCode,
        on_delete=models.CASCADE,
        related_name="clicks",
    )

    class Meta:
        ordering = ["-created"]


class Referral(UUIDModel, TimeStampedModel):
    referral_code = models.ForeignKey(
        ReferralCode,
        on_delete=models.PROTECT,
        related_name="referrals",
    )
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="referrals_made",
    )
    referred = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="referral_received",
    )
    signed_up_at = models.DateTimeField()
    converted_at = models.DateTimeField(null=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)
    referrer_credits_awarded = models.PositiveSmallIntegerField(default=0)
    referred_credits_awarded = models.PositiveSmallIntegerField(default=0)
    is_suspicious = models.BooleanField(default=False)
    suspicion_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(referrer=models.F("referred")),
                name="referral_referrer_cannot_equal_referred",
            ),
        ]

    @property
    def status(self):
        if self.rewarded_at:
            return "rewarded"
        if self.converted_at:
            return "converted"
        return "signed_up"

    def __str__(self):
        return f"{self.referrer} referred {self.referred}"
