from django.contrib import admin

from apps.members.models import Member, Reservation, WaitlistEntry


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created", "modified")
    search_fields = ("user__email", "phone_number")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "schedule",
        "spot",
        "schedule__duration_minutes",
        "schedule__instructor",
        "status",
    )
    list_filter = ("created", "schedule__start_time", "status")
    search_fields = ("member__user__email", "schedule__title", "schedule__instructor__user__email")


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "schedule",
        "status",
        "offered_spot",
        "offer_expires_at",
        "created",
    )
    list_filter = ("status", "created", "schedule__start_time")
    search_fields = ("member__user__email", "schedule__title")
