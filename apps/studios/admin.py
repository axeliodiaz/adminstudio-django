from django.contrib import admin

from apps.studios.models import Room, Studio


class StudioAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "is_active")
    list_filter = ("is_active", "created")


class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "studio", "capacity", "is_active")
    list_filter = ("is_active", "capacity", "created")


admin.site.register(Studio, StudioAdmin)
admin.site.register(Room, RoomAdmin)
