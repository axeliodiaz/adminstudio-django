from django.contrib import admin

from .models import Rider


@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created", "modified")
    search_fields = ("user__email", "phone_number")
