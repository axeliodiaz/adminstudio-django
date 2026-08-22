from django.contrib import admin

from apps.coach.models import (
    ClassPlaylist,
    ClassRating,
    PlaylistSegment,
    PlaylistTemplate,
    PlaylistTrack,
)


class SuperuserAddDeleteMixin:
    def has_add_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)


@admin.register(ClassRating)
class ClassRatingAdmin(SuperuserAddDeleteMixin, admin.ModelAdmin):
    list_display = ("schedule", "rating", "rating_count")
    search_fields = ("schedule__title",)
    raw_id_fields = ("schedule",)
    readonly_fields = ("id", "created", "modified")


@admin.register(PlaylistTemplate)
class PlaylistTemplateAdmin(SuperuserAddDeleteMixin, admin.ModelAdmin):
    list_display = ("name", "instructor", "class_format")
    search_fields = ("name", "instructor__user__username")
    autocomplete_fields = ("instructor",)
    readonly_fields = ("id", "created", "modified")


class PlaylistTrackInline(admin.TabularInline):
    model = PlaylistTrack
    extra = 0


class PlaylistSegmentInline(admin.TabularInline):
    model = PlaylistSegment
    extra = 0


@admin.register(ClassPlaylist)
class ClassPlaylistAdmin(SuperuserAddDeleteMixin, admin.ModelAdmin):
    list_display = ("title", "schedule", "instructor", "total_duration_minutes")
    search_fields = ("title", "schedule__title", "instructor__user__username")
    raw_id_fields = ("schedule",)
    autocomplete_fields = ("instructor",)
    readonly_fields = ("id", "created", "modified")
    inlines = [PlaylistSegmentInline]


@admin.register(PlaylistSegment)
class PlaylistSegmentAdmin(SuperuserAddDeleteMixin, admin.ModelAdmin):
    list_display = ("name", "playlist", "order", "duration_minutes", "bpm_range")
    search_fields = ("name",)
    autocomplete_fields = ("playlist",)
    readonly_fields = ("id", "created", "modified")
    inlines = [PlaylistTrackInline]


@admin.register(PlaylistTrack)
class PlaylistTrackAdmin(SuperuserAddDeleteMixin, admin.ModelAdmin):
    list_display = ("title", "artist", "segment", "bpm", "order")
    search_fields = ("title", "artist")
    autocomplete_fields = ("segment",)
    readonly_fields = ("id", "created", "modified")
