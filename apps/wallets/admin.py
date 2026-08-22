from django.contrib import admin

from apps.wallets.models import PlanPurchase, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "class_credits",
        "guest_pass_credits",
        "active_membership_end_date",
        "is_priority_booker",
        "is_unlimited_membership_active",
        "created",
    )
    list_filter = (
        "is_priority_booker",
        "can_freeze_membership",
        "is_founders_exclusive",
        "is_unlimited_membership_active",
        "created",
    )
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")
    readonly_fields = ("id", "created", "modified")
    fieldsets = (
        ("User", {"fields": ("user",)}),
        (
            "Credits",
            {
                "fields": (
                    "class_credits",
                    "guest_pass_credits",
                )
            },
        ),
        (
            "Membership",
            {
                "fields": (
                    "active_membership_end_date",
                    "is_unlimited_membership_active",
                    "retail_discount_percentage",
                )
            },
        ),
        (
            "Benefits",
            {
                "fields": (
                    "is_priority_booker",
                    "can_freeze_membership",
                    "is_founders_exclusive",
                )
            },
        ),
        ("Metadata", {"fields": ("id", "created", "modified"), "classes": ("collapse",)}),
    )


@admin.register(PlanPurchase)
class PlanPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "plan",
        "price_paid",
        "quantity",
        "promo_code",
        "payment_method",
        "activated_since",
        "created",
    )
    list_filter = (
        "activated_since",
        "plan__type",
        "created",
    )
    search_fields = (
        "user__email",
        "user__username",
        "user__first_name",
        "user__last_name",
        "plan__name",
    )
    readonly_fields = ("id", "created", "modified")
    fieldsets = (
        (
            "Purchase Details",
            {
                "fields": (
                    "user",
                    "plan",
                    "quantity",
                    "price_paid",
                    "discount_amount",
                    "promo_code",
                    "payment_method",
                    "activated_since",
                    "start",
                    "end",
                )
            },
        ),
        ("Metadata", {"fields": ("id", "created", "modified"), "classes": ("collapse",)}),
    )
    date_hierarchy = "created"
