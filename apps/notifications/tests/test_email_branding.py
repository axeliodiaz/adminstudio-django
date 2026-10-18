from unittest.mock import patch

import pytest
from model_bakery import baker

from apps.notifications.branding import email_branding
from apps.notifications.email_templates import render_password_recovery, render_welcome_email
from apps.studios.models import StudioBranding


def test_custom_theme_is_escaped_and_uses_contrast_and_fonts():
    html = render_welcome_email(
        first_name="Ana",
        classes_url="https://example.com/#classes",
        frontend_url="https://example.com",
        branding={
            "name": "Ritmo <script>alert(1)</script>",
            "primary_color": "#0D9488",
            "secondary_color": "#FFFFFF",
            "heading_font": "Playfair Display",
            "body_font": "Nunito",
            "logo_svg": "<svg/>",
            "studio_id": "a-studio",
        },
    )
    assert "Ritmo &lt;script&gt;" in html
    assert "<script>" not in html
    assert "#0D9488" in html
    assert "Playfair Display" in html and "Nunito" in html
    assert "color:#000000" in html
    assert "https://example.com/api/brand-logo?studio=a-studio" in html
    assert "PulseFit" not in html and "Patio Andino" not in html and "hola@pulsefit" not in html


def test_invalid_css_tokens_fall_back():
    html = render_password_recovery(
        reset_code="123456",
        frontend_url="https://example.com",
        branding={
            "primary_color": "red;position:fixed",
            "body_font": 'bad"font',
        },
    )
    assert "position:fixed" not in html and 'bad"font' not in html
    assert "#4F46E5" in html


@pytest.mark.django_db
def test_studio_override_then_default_without_cross_studio_leak():
    a, b = baker.make("studios.Studio", _quantity=2)
    StudioBranding.objects.create(studio=None, name="Red", primary_color="#123456")
    StudioBranding.objects.create(studio=a, name="Ritmo", primary_color="#0D9488")
    assert email_branding(a)["name"] == "Ritmo"
    assert email_branding(b)["name"] == "Red"
    assert email_branding()["name"] == "Red"


@pytest.mark.django_db
def test_reservation_uses_its_class_studio(base_graph):
    from apps.members.notifications import send_reservation_confirmed_email

    member, instructor, room = base_graph
    StudioBranding.objects.create(studio=room.studio, name="Local A", primary_color="#0D9488")
    schedule = baker.make("schedules.Schedule", room=room, instructor=instructor)
    reservation = baker.make("members.Reservation", member=member, schedule=schedule, spot=1)
    with patch("apps.members.notifications.create_notification") as send:
        send_reservation_confirmed_email(reservation)
    assert send.call_count == 1
    assert "Local A" in send.call_args.kwargs["html_content"]
    assert "#0D9488" in send.call_args.kwargs["html_content"]


def test_dark_background_keeps_configured_text_on_body_and_details():
    html = render_password_recovery(
        reset_code="123456",
        frontend_url="https://example.com",
        branding={
            "background_color": "#111827",
            "text_color": "#F9FAFB",
            "primary_color": "#A5B4FC",
        },
    )
    assert "#595959" not in html
    assert "color:#F9FAFB" in html
    assert "background-color:#111827" in html
