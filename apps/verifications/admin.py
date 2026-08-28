from django.contrib import admin

from .models import VerificationCode


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "masked_code",
        "has_confirmed",
        "expires_at",
        "created",
    )
    list_filter = ("has_confirmed", "expires_at", "created")
    date_hierarchy = "created"
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = (
        "id",
        "user",
        "has_confirmed",
        "expires_at",
        "created",
        "modified",
    )
    ordering = ("-created",)

    @admin.display(description="Code")
    def masked_code(self, obj):
        return f"{obj.code[:2]}{'*' * max(len(obj.code) - 2, 0)}"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
