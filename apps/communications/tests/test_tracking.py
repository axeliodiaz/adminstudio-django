"""Click tracking: redirect endpoint, counters and admin APIs (CYC-396)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken

from apps.communications.models import TrackedLink
from apps.communications.tracking import validate_target_url

User = get_user_model()


def make_user(username, **kwargs):
    defaults = {"email": f"{username}@example.com", "password": "testpass123"}
    defaults.update(kwargs)
    return User.objects.create_user(username=username, **defaults)


@pytest.fixture
def staff_client(api_client):
    staff = make_user("tracking.admin", is_staff=True)
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


class TestValidateTargetUrl:
    def test_accepts_http_and_https(self):
        assert validate_target_url("https://example.com/x") == "https://example.com/x"
        assert validate_target_url("http://example.com") == "http://example.com"

    @pytest.mark.parametrize("url", ["", "ftp://x.com", "javascript:alert(1)", "/relative", "example.com"])
    def test_rejects_bad_urls(self, url):
        with pytest.raises(ValueError):
            validate_target_url(url)


@pytest.mark.django_db
class TestTrackedLinkAdminApi:
    def test_create_link_for_recipient_user(self, staff_client):
        rider = make_user("link.rider")
        response = staff_client.post(
            reverse("communications-links"),
            {
                "target_url": "https://studio.axeldiaz.com/#pricing",
                "label": "Promo",
                "user_id": str(rider.id),
            },
            format="json",
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["recipient_email"] == rider.email
        assert payload["user_id"] == str(rider.id)
        assert payload["token"]
        assert payload["redirect_path"].endswith(f"/r/{payload['token']}/")
        assert payload["redirect_url"].startswith("http")

    def test_create_rejects_invalid_url(self, staff_client):
        response = staff_client.post(
            reverse("communications-links"),
            {"target_url": "javascript:alert(1)"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_rejects_unknown_user(self, staff_client):
        response = staff_client.post(
            reverse("communications-links"),
            {"target_url": "https://example.com", "user_id": "nope"},
            format="json",
        )
        assert response.status_code == 400

    def test_list_is_paginated(self, staff_client):
        for index in range(3):
            TrackedLink.objects.create(target_url=f"https://example.com/{index}")
        response = staff_client.get(reverse("communications-links"), {"page_size": 2})
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 3
        assert len(payload["results"]) == 2
        assert payload["next_page"] == 2

    def test_detail_includes_recent_clicks(self, staff_client, api_client):
        link = TrackedLink.objects.create(target_url="https://example.com")
        api_client.get(reverse("communications-link-redirect", args=[link.token]))
        response = staff_client.get(reverse("communications-link-detail", args=[link.id]))
        assert response.status_code == 200
        payload = response.json()
        assert payload["click_count"] == 1
        assert len(payload["recent_clicks"]) == 1

    def test_member_forbidden(self, api_client):
        member = make_user("member.tracking")
        token = ExpiringToken.objects.create(user=member)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        assert api_client.get(reverse("communications-links")).status_code == 403


@pytest.mark.django_db
class TestTrackedLinkRedirect:
    def test_redirect_records_click_and_counters(self, api_client):
        link = TrackedLink.objects.create(
            target_url="https://example.com/landing",
            recipient_email="rider@example.com",
        )
        url = reverse("communications-link-redirect", args=[link.token])
        first = api_client.get(url, HTTP_USER_AGENT="pytest-agent")
        assert first.status_code == 302
        assert first["Location"] == "https://example.com/landing"
        api_client.get(url)
        link.refresh_from_db()
        assert link.click_count == 2
        assert link.first_clicked_at is not None
        assert link.last_clicked_at >= link.first_clicked_at
        click = link.clicks.first()
        assert click.user_agent == "pytest-agent"
        assert click.ip_hash and click.ip_hash != "127.0.0.1"

    def test_unknown_token_404(self, api_client):
        response = api_client.get(reverse("communications-link-redirect", args=["nope"]))
        assert response.status_code == 404

    def test_inactive_link_404_and_no_click(self, api_client):
        link = TrackedLink.objects.create(
            target_url="https://example.com", is_active=False
        )
        response = api_client.get(reverse("communications-link-redirect", args=[link.token]))
        assert response.status_code == 404
        link.refresh_from_db()
        assert link.click_count == 0

    def test_tokens_are_unique_per_link(self):
        first = TrackedLink.objects.create(target_url="https://example.com")
        second = TrackedLink.objects.create(target_url="https://example.com")
        assert first.token != second.token
