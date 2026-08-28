from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "subject",
        "transport",
        "status",
        "created",
        "modified",
    )
    list_filter = ("status", "transport", "created")
    date_hierarchy = "created"
    search_fields = ("subject", "message", "user__email", "user__first_name", "user__last_name")
    readonly_fields = (
        "id",
        "user",
        "subject",
        "message",
        "html_content",
        "transport",
        "created",
        "modified",
    )
    ordering = ("-created",)

    def has_add_permission(self, request):
        return False
