import pytest
from django.contrib.admin.sites import AdminSite
from model_bakery import baker

from apps.notifications.admin import NotificationAdmin
from apps.notifications.models import Notification


@pytest.mark.django_db
class TestNotificationDjangoAdmin:
    def test_html_preview_embeds_email_in_iframe(self):
        notification = baker.make(
            "notifications.Notification",
            html_content='<html><body><h1 class="title">Confirma tu correo</h1></body></html>',
        )
        model_admin = NotificationAdmin(Notification, AdminSite())

        preview = str(model_admin.html_preview(notification))

        assert "<iframe" in preview
        assert 'srcdoc="' in preview
        assert "<h1 class=&quot;title&quot;>Confirma tu correo</h1>" in preview
        assert "<em>Sin contenido HTML</em>" not in preview

    def test_html_preview_empty_shows_placeholder(self):
        notification = baker.make("notifications.Notification", html_content="")
        model_admin = NotificationAdmin(Notification, AdminSite())

        preview = str(model_admin.html_preview(notification))

        assert "Sin contenido HTML" in preview
        assert "<iframe" not in preview
