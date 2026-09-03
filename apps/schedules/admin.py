from django.contrib import admin

from apps.schedules.models import Schedule, ScheduleInstructorSubstitution


class ScheduleInstructorSubstitutionInline(admin.TabularInline):
    model = ScheduleInstructorSubstitution
    extra = 0
    can_delete = False
    readonly_fields = (
        "old_instructor",
        "new_instructor",
        "changed_by",
        "reason",
        "notify",
        "reserved_notified",
        "waitlist_notified",
        "created",
    )
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("title", "start_time", "duration_minutes", "instructor", "room", "status")
    list_filter = ("start_time", "duration_minutes", "instructor__user__username", "status")
    inlines = [ScheduleInstructorSubstitutionInline]


@admin.register(ScheduleInstructorSubstitution)
class ScheduleInstructorSubstitutionAdmin(admin.ModelAdmin):
    list_display = (
        "created",
        "schedule",
        "old_instructor",
        "new_instructor",
        "changed_by",
        "notify",
        "reserved_notified",
        "waitlist_notified",
    )
    list_filter = ("notify", "created")
    search_fields = (
        "schedule__title",
        "reason",
        "old_instructor__user__first_name",
        "new_instructor__user__first_name",
        "changed_by__email",
    )
    readonly_fields = (
        "schedule",
        "old_instructor",
        "new_instructor",
        "changed_by",
        "reason",
        "notify",
        "reserved_notified",
        "waitlist_notified",
        "created",
        "modified",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(Schedule, ScheduleAdmin)
