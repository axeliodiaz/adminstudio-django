from django.contrib import admin

from apps.schedules.models import Schedule


class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "start_time", "duration_minutes", "instructor", "room", "status")
    list_filter = ("start_time", "duration_minutes", "instructor__user__username", "status")


admin.site.register(Schedule, ScheduleAdmin)
