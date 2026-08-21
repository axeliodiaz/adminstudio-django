from django.contrib import admin
from django.utils.html import format_html
from markdown import markdown

from apps.faq.models import Section, FAQItem


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "faq_count", "created")
    list_editable = ("order",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}

    def faq_count(self, obj):
        """Show count of FAQ items in this section."""
        count = obj.faq_items.filter(is_deleted=False).count()
        return count

    faq_count.short_description = "Preguntas"


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ("question", "section", "order", "is_published", "preview_answer", "created")
    list_filter = ("section", "is_published", "created")
    list_editable = ("order", "is_published")
    search_fields = ("question", "answer")
    autocomplete_fields = ("section",)

    fieldsets = (
        (
            "Información básica",
            {
                "fields": ("section", "question", "order", "is_published"),
            },
        ),
        (
            "Respuesta (Markdown)",
            {
                "fields": ("answer",),
                "description": "Puedes usar Markdown para formatear la respuesta. "
                "Ejemplo: **negrita**, *cursiva*, [enlaces](url), listas, etc.",
            },
        ),
        (
            "Vista previa",
            {
                "fields": ("answer_preview",),
            },
        ),
    )

    readonly_fields = ("answer_preview",)

    def preview_answer(self, obj):
        """Show a short preview of the answer."""
        if obj.answer:
            preview = obj.answer[:100] + "..." if len(obj.answer) > 100 else obj.answer
            return preview
        return "-"

    preview_answer.short_description = "Vista previa"

    def answer_preview(self, obj):
        """Show rendered markdown preview in admin."""
        if obj.answer:
            html = markdown(obj.answer, extensions=["extra", "codehilite"])
            return format_html(
                '<div style="padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9;">{}</div>',
                html,
            )
        return format_html("<em>No hay respuesta aún</em>")

    answer_preview.short_description = "Vista previa renderizada"
