from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone_number",
                    "gender",
                    "birthdate",
                    "height_cm",
                    "weight_kg",
                    "address",
                )
            },
        ),
        (
            "Cycling",
            {
                "fields": (
                    "seat_height",
                    "seat_distance",
                    "handlebar_distance",
                    "cycling_shoe_size",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "gender",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    list_display = (
        "id",
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "gender",
        "is_staff",
    )
    search_fields = ("email", "first_name", "last_name", "phone_number")
    ordering = ("id",)
