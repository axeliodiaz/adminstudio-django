import secrets
import string

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.referrals.models import Referral, ReferralClick, ReferralCode, ReferralProgramSettings
from apps.wallets.models import Wallet

CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_LENGTH = 8


def get_program_settings() -> ReferralProgramSettings:
    settings, _ = ReferralProgramSettings.objects.get_or_create(pk=1)
    return settings


def get_or_create_referral_code(*, user) -> ReferralCode:
    existing = ReferralCode.objects.filter(user=user).first()
    if existing:
        return existing

    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        try:
            return ReferralCode.objects.create(user=user, code=code)
        except IntegrityError:
            continue


def get_valid_referral_code(*, code: str) -> ReferralCode:
    normalized_code = (code or "").strip().upper()
    referral_code = ReferralCode.objects.filter(code=normalized_code, is_active=True).first()
    if not referral_code or (
        referral_code.expires_at and referral_code.expires_at <= timezone.now()
    ):
        raise ValueError("El código de referido es inválido o expiró.")
    if not get_program_settings().is_active:
        raise ValueError("El programa de referidos no está activo.")
    return referral_code


def record_click(*, code: str, user=None) -> None:
    referral_code = get_valid_referral_code(code=code)
    if user and user.is_authenticated and user == referral_code.user:
        raise ValueError("No puedes usar tu propio código de referido.")
    ReferralClick.objects.create(referral_code=referral_code)


def attribute_signup(*, referred_user, code: str | None) -> Referral | None:
    if not code:
        return None

    referral_code = get_valid_referral_code(code=code)
    if referral_code.user_id == referred_user.id:
        raise ValueError("No puedes usar tu propio código de referido.")

    return Referral.objects.create(
        referral_code=referral_code,
        referrer=referral_code.user,
        referred=referred_user,
        signed_up_at=timezone.now(),
    )


def reward_first_purchase(*, user) -> Referral | None:
    """Reward a referral once after the referred member's first activated purchase."""
    with transaction.atomic():
        referral = (
            Referral.objects.select_for_update()
            .select_related("referrer", "referred")
            .filter(referred=user, rewarded_at__isnull=True)
            .first()
        )
        if not referral:
            return None

        settings = get_program_settings()
        referral.converted_at = timezone.now()
        if not settings.is_active:
            referral.save(update_fields=["converted_at", "modified"])
            return referral

        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rewarded_this_month = Referral.objects.filter(
            referrer=referral.referrer,
            rewarded_at__gte=month_start,
        ).count()
        if rewarded_this_month >= settings.monthly_referrer_reward_limit:
            referral.save(update_fields=["converted_at", "modified"])
            return referral

        referrer_wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=referral.referrer
        )
        referred_wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=referral.referred
        )
        referrer_wallet.class_credits += settings.referrer_credit_reward
        referred_wallet.class_credits += settings.referred_credit_reward
        referrer_wallet.save(update_fields=["class_credits", "modified"])
        referred_wallet.save(update_fields=["class_credits", "modified"])

        referral.rewarded_at = timezone.now()
        referral.referrer_credits_awarded = settings.referrer_credit_reward
        referral.referred_credits_awarded = settings.referred_credit_reward
        referral.save(
            update_fields=[
                "converted_at",
                "rewarded_at",
                "referrer_credits_awarded",
                "referred_credits_awarded",
                "modified",
            ]
        )
        return referral


def referral_dashboard(*, user) -> dict:
    code = get_or_create_referral_code(user=user)
    referrals = Referral.objects.filter(referrer=user).select_related("referred")
    return {
        "code": code.code,
        "is_active": code.is_active,
        "pending_count": referrals.filter(rewarded_at__isnull=True).count(),
        "rewarded_count": referrals.filter(rewarded_at__isnull=False).count(),
        "referrals": [
            {
                "id": referral.id,
                "name": referral.referred.get_full_name() or referral.referred.username,
                "status": referral.status,
                "signed_up_at": referral.signed_up_at,
                "rewarded_at": referral.rewarded_at,
            }
            for referral in referrals
        ],
    }


def admin_dashboard() -> dict:
    referrals = Referral.objects.select_related("referrer", "referred").all()
    rewarded = referrals.filter(rewarded_at__isnull=False)
    settings = get_program_settings()
    credits_awarded = (
        rewarded.aggregate(total=Sum("referrer_credits_awarded") + Sum("referred_credits_awarded"))[
            "total"
        ]
        or 0
    )
    return {
        "summary": {
            "clicks": ReferralClick.objects.count(),
            "sign_ups": referrals.count(),
            "rewarded": rewarded.count(),
            "credits_awarded": credits_awarded,
            "cost_per_acquisition": (
                round(credits_awarded / rewarded.count(), 2) if rewarded.exists() else 0
            ),
            "suspicious": referrals.filter(is_suspicious=True).count(),
        },
        "top_referrers": list(
            rewarded.values(
                "referrer__id",
                "referrer__first_name",
                "referrer__last_name",
                "referrer__email",
            )
            .annotate(rewarded_count=Count("id"))
            .order_by("-rewarded_count", "referrer__email")[:10]
        ),
        "referrals": [
            {
                "id": referral.id,
                "referrer": referral.referrer.get_full_name() or referral.referrer.email,
                "referred": referral.referred.get_full_name() or referral.referred.email,
                "status": referral.status,
                "signed_up_at": referral.signed_up_at,
                "converted_at": referral.converted_at,
                "rewarded_at": referral.rewarded_at,
                "referrer_credits_awarded": referral.referrer_credits_awarded,
                "referred_credits_awarded": referral.referred_credits_awarded,
                "is_suspicious": referral.is_suspicious,
                "suspicion_note": referral.suspicion_note,
            }
            for referral in referrals
        ],
        "settings": {
            "referrer_credit_reward": settings.referrer_credit_reward,
            "referred_credit_reward": settings.referred_credit_reward,
            "monthly_referrer_reward_limit": settings.monthly_referrer_reward_limit,
        },
    }
