from django.contrib import admin

from apps.referrals.models import Referral, ReferralClick, ReferralCode, ReferralProgramSettings


@admin.register(ReferralProgramSettings)
class ReferralProgramSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "is_active",
        "referrer_credit_reward",
        "referred_credit_reward",
        "monthly_referrer_reward_limit",
    )

    def has_add_permission(self, request):
        return not ReferralProgramSettings.objects.exists()


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "user", "is_active", "expires_at", "created")
    list_filter = ("is_active",)
    search_fields = ("code", "user__email", "user__username")
    readonly_fields = ("id", "created", "modified")


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        "referrer",
        "referred",
        "status",
        "signed_up_at",
        "converted_at",
        "rewarded_at",
        "referrer_credits_awarded",
        "referred_credits_awarded",
    )
    list_filter = ("is_suspicious", "rewarded_at", "converted_at", "signed_up_at")
    search_fields = (
        "referral_code__code",
        "referrer__email",
        "referrer__username",
        "referred__email",
        "referred__username",
    )
    readonly_fields = (
        "id",
        "referral_code",
        "referrer",
        "referred",
        "signed_up_at",
        "converted_at",
        "rewarded_at",
        "referrer_credits_awarded",
        "referred_credits_awarded",
        "created",
        "modified",
    )

    @admin.display(description="Status")
    def status(self, referral):
        return referral.status


@admin.register(ReferralClick)
class ReferralClickAdmin(admin.ModelAdmin):
    list_display = ("referral_code", "created")
    search_fields = ("referral_code__code", "referral_code__user__email")
    readonly_fields = ("id", "referral_code", "created", "modified")
