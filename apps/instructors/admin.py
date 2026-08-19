from django.contrib import admin

from apps.instructors.models import Instructor


class InstructorAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "email",
        "tagline",
        "location",
        "is_verified",
        "is_active",
    )
    list_filter = ("is_verified", "user__is_active")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "user__username",
        "tagline",
        "location",
        "instagram_username",
    )
    autocomplete_fields = ("user",)
    readonly_fields = ("id", "created", "modified")
    fieldsets = (
        (None, {"fields": ("id", "user", "profile_image")}),
        (
            "Perfil público",
            {
                "fields": (
                    "tagline",
                    "description",
                    "location",
                    "instructor_since",
                    "is_verified",
                )
            },
        ),
        (
            "Redes",
            {
                "fields": (
                    "website_url",
                    "instagram_username",
                    "tiktok_username",
                )
            },
        ),
        (
            "Playlists",
            {
                "fields": (
                    "last_spotify_playlist",
                    "last_apple_music_playlist",
                    "last_youtube_music_playlist",
                )
            },
        ),
        ("Auditoría", {"fields": ("created", "modified")}),
    )

    def email(self, obj):
        return obj.user.email

    def is_active(self, obj):
        return obj.user.is_active

    is_active.boolean = True

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)


admin.site.register(Instructor, InstructorAdmin)
