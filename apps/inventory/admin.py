from django.contrib import admin

from apps.inventory.models import Category, Item, Location


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "kind")
    list_filter = ("kind",)
    search_fields = ("name",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "location", "spot", "identifier", "is_active")
    list_filter = ("category", "location", "is_active")
    search_fields = ("name", "identifier", "spot")
