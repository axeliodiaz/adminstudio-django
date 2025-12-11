from django import forms
from django.contrib import admin

from apps.studios.models import Address, Room, Studio


class AddressAdminForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = "__all__"
        widgets = {
            "address": forms.TextInput(
                attrs={
                    "class": "vTextField address-autocomplete",
                    "placeholder": "Escribe una dirección",
                    "autocomplete": "off",
                }
            ),
            "latitude": forms.TextInput(
                attrs={
                    "class": "vTextField",
                    "readonly": "readonly",
                }
            ),
            "longitude": forms.TextInput(
                attrs={
                    "class": "vTextField",
                    "readonly": "readonly",
                }
            ),
        }

    class Media:
        css = {"all": ("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",)}
        js = (
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
            "studios/js/address_admin.js",
        )


class AddressAdmin(admin.ModelAdmin):
    form = AddressAdminForm
    list_display = ("address", "latitude", "longitude", "created")
    search_fields = ("address",)


class StudioAdmin(admin.ModelAdmin):
    list_display = ("name", "opening_time", "closing_time", "address", "is_active")
    list_filter = ("is_active", "created")
    autocomplete_fields = ("address",)


class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "studio", "capacity", "is_active")
    list_filter = ("is_active", "capacity", "created")


admin.site.register(Address, AddressAdmin)
admin.site.register(Studio, StudioAdmin)
admin.site.register(Room, RoomAdmin)
