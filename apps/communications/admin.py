from django.contrib import admin

from apps.communications.models import TrackedLink, TrackedLinkClick


@admin.register(TrackedLink)
class TrackedLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "target_url", "recipient_email", "click_count", "is_active")
    list_filter = ("is_active",)
    search_fields = ("label", "target_url", "recipient_email", "token")
    readonly_fields = ("token", "click_count", "first_clicked_at", "last_clicked_at")


@admin.register(TrackedLinkClick)
class TrackedLinkClickAdmin(admin.ModelAdmin):
    list_display = ("link", "created")
    readonly_fields = ("link", "user_agent", "ip_hash")
