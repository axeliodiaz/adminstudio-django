from django.contrib import admin

from apps.plans.models import Plan, Benefit


class BenefitInline(admin.TabularInline):
    model = Benefit


class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "display_type",
        "duration_days",
        "classes_included",
        "is_active",
        "is_highlighted",
        "is_popular",
    )
    list_filter = ("is_active", "type", "created")
    search_fields = ("name", "benefits__name")
    filter_horizontal = ("benefits",)

    def display_type(self, obj):
        return obj.get_type_display()

    display_type.short_description = "Type"


class BenefitAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "is_active")
    list_filter = ("name",)


admin.site.register(Plan, PlanAdmin)
admin.site.register(Benefit, BenefitAdmin)
