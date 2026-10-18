from django.contrib import admin

from apps.reports.models import ClassMetrics, DailyMetrics


@admin.register(DailyMetrics)
class DailyMetricsAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "studio",
        "reservations_booked",
        "reservations_attended",
        "revenue",
        "computed_at",
    )
    list_filter = ("studio",)
    date_hierarchy = "date"
    readonly_fields = ("computed_at",)


@admin.register(ClassMetrics)
class ClassMetricsAdmin(admin.ModelAdmin):
    list_display = ("date", "title", "instructor", "booked", "capacity", "occupancy_rate", "rating")
    list_filter = ("is_canceled", "studio")
    date_hierarchy = "date"
    readonly_fields = ("computed_at",)
