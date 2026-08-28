import html as html_lib

from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Notification


def _srcdoc_attr(html_content: str) -> str:
    """Escape only what would break a double-quoted srcdoc attribute.

    ``format_html`` / ``html.escape`` would also encode ``<``/``>``, which
    makes the iframe show source instead of rendering the email.
    """
    return html_content.replace("&", "&amp;").replace('"', "&quot;")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "subject",
        "transport",
        "status",
        "created",
        "modified",
    )
    list_filter = ("status", "transport", "created")
    date_hierarchy = "created"
    search_fields = ("subject", "message", "user__email", "user__first_name", "user__last_name")
    readonly_fields = (
        "id",
        "user",
        "subject",
        "message",
        "html_preview",
        "transport",
        "created",
        "modified",
    )
    ordering = ("-created",)

    def has_add_permission(self, request):
        return False

    @admin.display(description="Html content")
    def html_preview(self, obj):
        if not obj or not (obj.html_content or "").strip():
            return mark_safe("<em>Sin contenido HTML</em>")

        srcdoc = _srcdoc_attr(obj.html_content)
        source = html_lib.escape(obj.html_content)
        return mark_safe(
            "<div>"
            f'<iframe srcdoc="{srcdoc}" sandbox="" '
            'style="width:100%;height:640px;border:1px solid #555;border-radius:6px;'
            'background:#fff;" title="Vista previa del correo"></iframe>'
            '<details style="margin-top:8px;">'
            "<summary>Ver código HTML</summary>"
            f'<pre style="max-height:240px;overflow:auto;white-space:pre-wrap;'
            f'word-break:break-word;">{source}</pre>'
            "</details>"
            "</div>"
        )
