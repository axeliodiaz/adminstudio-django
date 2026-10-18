"""Composer variables, preview rendering and channel metadata (CYC-394)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from model_bakery import baker

from apps.communications import composer

User = get_user_model()


def make_user(username, **kwargs):
    defaults = {"email": f"{username}@example.com", "password": "testpass123"}
    defaults.update(kwargs)
    return User.objects.create_user(username=username, **defaults)


@pytest.fixture
def staff_client(api_client):
    staff = make_user("composer.admin", is_staff=True, is_superuser=True)
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestRenderTemplate:
    def test_renders_variables_for_user(self):
        user = make_user("rider", first_name="María", last_name="Pérez")
        baker.make("wallets.Wallet", user=user, class_credits=7)
        assert composer.render_template("Hola {{ first_name }}!", user) == "Hola María!"
        assert "7" in composer.render_template("Te quedan {{remaining_credits}} créditos.", user)

    def test_name_falls_back_to_username(self):
        user = make_user("noname")
        assert composer.render_template("{{ name }}", user) == "noname"

    def test_user_without_wallet_has_zero_credits(self):
        user = make_user("nowallet")
        assert composer.render_template("{{ remaining_credits }}", user) == "0"

    def test_sample_values_without_user(self):
        rendered = composer.render_template("Hola {{ first_name }} ({{ remaining_credits }})")
        assert rendered == "Hola Alex (5)"

    def test_unknown_variable_raises(self):
        with pytest.raises(composer.ComposerError):
            composer.render_template("Hola {{ nickname }}")

    def test_find_unknown_variables(self):
        assert composer.find_unknown_variables("{{ name }} {{ phone }}") == ["phone"]


@pytest.mark.django_db
class TestComposerEndpoints:
    def test_channels_email_enabled_sms_whatsapp_disabled(self, staff_client):
        response = staff_client.get(reverse("communications-channels"))
        assert response.status_code == 200
        channels = {c["id"]: c for c in response.json()["channels"]}
        assert channels["email"]["enabled"] is True
        assert channels["sms"]["enabled"] is False
        assert channels["whatsapp"]["enabled"] is False
        assert channels["sms"]["reason"]

    def test_variables_endpoint(self, staff_client):
        response = staff_client.get(reverse("communications-composer-variables"))
        assert response.status_code == 200
        keys = {v["key"] for v in response.json()["variables"]}
        assert {"name", "first_name", "remaining_credits"} <= keys

    def test_preview_renders_for_sample_user(self, staff_client):
        rider = make_user("preview.rider", first_name="Camila")
        baker.make("wallets.Wallet", user=rider, class_credits=3)
        response = staff_client.post(
            reverse("communications-composer-preview"),
            {
                "subject": "Hola {{ first_name }}",
                "message": "Te quedan {{ remaining_credits }} créditos.",
                "sample_user_id": str(rider.id),
            },
            format="json",
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["subject"] == "Hola Camila"
        assert "3 créditos" in payload["message"]
        assert payload["sample_user"]["email"] == rider.email

    def test_preview_uses_sample_values_without_user(self, staff_client):
        response = staff_client.post(
            reverse("communications-composer-preview"),
            {"message": "Hola {{ first_name }}"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Hola Alex"

    def test_preview_rejects_unknown_variable(self, staff_client):
        response = staff_client.post(
            reverse("communications-composer-preview"),
            {"message": "Hola {{ nickname }}"},
            format="json",
        )
        assert response.status_code == 400
        assert "nickname" in response.json()["detail"]

    def test_preview_rejects_bad_sample_user(self, staff_client):
        response = staff_client.post(
            reverse("communications-composer-preview"),
            {"message": "Hola", "sample_user_id": "not-a-uuid"},
            format="json",
        )
        assert response.status_code == 400

    def test_preview_requires_message(self, staff_client):
        response = staff_client.post(
            reverse("communications-composer-preview"), {"message": "  "}, format="json"
        )
        assert response.status_code == 400

    def test_member_forbidden(self, api_client):
        member = make_user("member.composer")
        token = ExpiringToken.objects.create(user=member)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        assert api_client.get(reverse("communications-channels")).status_code == 403
