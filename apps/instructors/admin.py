from django.contrib import admin

from apps.instructors.models import Instructor


class InstructorAdmin(admin.ModelAdmin):
    list_display = ("user",)


admin.site.register(Instructor, InstructorAdmin)
