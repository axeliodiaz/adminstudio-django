from django.contrib import admin
from django.utils.html import format_html
from markdown import markdown

from apps.legal.models import LegalDocument


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "document_type",
        "language",
        "version",
        "effective_date",
        "is_published",
        "preview_content",
        "created",
    )
    list_filter = ("document_type", "language", "is_published", "effective_date", "created")
    list_editable = ("is_published",)
    search_fields = ("title", "slug", "content")
    prepopulated_fields = {"slug": ("title",)}

    fieldsets = (
        (
            "Información básica",
            {
                "fields": (
                    "document_type",
                    "title",
                    "slug",
                    "language",
                    "version",
                    "effective_date",
                    "order",
                    "is_published",
                ),
            },
        ),
        (
            "Contenido (Markdown)",
            {
                "fields": ("content",),
                "description": "Puedes usar Markdown para formatear el contenido. "
                "Ejemplo: **negrita**, *cursiva*, [enlaces](url), listas, etc.",
            },
        ),
        (
            "Vista previa",
            {
                "fields": ("content_preview",),
            },
        ),
    )

    readonly_fields = ("content_preview",)

    def preview_content(self, obj):
        """Show a short preview of the content."""
        if obj.content:
            preview = obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
            return preview
        return "-"

    preview_content.short_description = "Vista previa"

    def content_preview(self, obj):
        """Show rendered markdown preview in admin."""
        if obj.content:
            html = markdown(obj.content, extensions=["extra", "codehilite"])
            return format_html(
                '<div style="padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9;">{}</div>',
                html,
            )
        return format_html("<em>No hay contenido aún</em>")

    content_preview.short_description = "Vista previa renderizada"
