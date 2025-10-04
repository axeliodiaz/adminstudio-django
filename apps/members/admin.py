from django.contrib import admin

from apps.members.models import Member, Reservation


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created", "modified")
    search_fields = ("user__email", "phone_number")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("member", "schedule", "status")
    list_filter = ("status",)
