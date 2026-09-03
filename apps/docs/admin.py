from django import forms
from django.contrib import admin
from django_ckeditor_5.widgets import CKEditor5Widget

from apps.docs.models import DocPage, DocSection


class DocPageAdminForm(forms.ModelForm):
    body = forms.CharField(
        required=False,
        widget=CKEditor5Widget(config_name="default", attrs={"class": "django_ckeditor_5"}),
        help_text="Cuerpo HTML. Se sanitiza al guardar (se eliminan scripts y markup inseguro).",
    )

    class Meta:
        model = DocPage
        fields = "__all__"


@admin.register(DocSection)
class DocSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "slug", "order", "is_published", "page_count", "created")
    list_filter = ("audience", "is_published")
    list_editable = ("order", "is_published")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}

    def page_count(self, obj):
        return obj.pages.filter(is_removed=False).count()

    page_count.short_description = "Artículos"


@admin.register(DocPage)
class DocPageAdmin(admin.ModelAdmin):
    form = DocPageAdminForm
    list_display = (
        "title",
        "section",
        "slug",
        "order",
        "is_published",
        "related_app_route",
        "created",
    )
    list_filter = ("is_published", "section__audience", "section")
    list_editable = ("order", "is_published")
    search_fields = ("title", "slug", "summary", "body")
    autocomplete_fields = ("section",)
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (
            "Información básica",
            {
                "fields": (
                    "section",
                    "title",
                    "slug",
                    "summary",
                    "order",
                    "is_published",
                    "related_app_route",
                ),
            },
        ),
        (
            "Cuerpo",
            {"fields": ("body",)},
        ),
    )
