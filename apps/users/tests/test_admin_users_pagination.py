"""Opt-in pagination on the staff users list (CYC-80 phase 2)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken

User = get_user_model()


@pytest.fixture
def staff_client(api_client):
    staff = User.objects.create_user(
        username="staffer", email="staff@example.com", password="x", is_staff=True
    )
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def users(db):
    rows = []
    for i in range(7):
        rows.append(
            User.objects.create_user(
                username=f"u{i}@ex.com",
                email=f"u{i}@ex.com",
                password="x",
                first_name=f"Ana{i:02d}",
            )
        )
    return rows


@pytest.mark.django_db
class TestAdminUsersPagination:
    def test_without_page_params_returns_plain_list(self, staff_client, users):
        resp = staff_client.get(reverse("users:users"))
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_page_envelope(self, staff_client, users):
        resp = staff_client.get(reverse("users:users"), {"page": 2, "page_size": 3})
        assert resp.status_code == 200
        body = resp.data
        assert body["page"] == 2
        assert body["page_size"] == 3
        assert body["next_page"] == 3
        assert body["previous_page"] == 1
        assert len(body["results"]) == 3

    def test_search_applies_before_paging(self, staff_client, users):
        resp = staff_client.get(
            reverse("users:users"), {"search": "Ana03", "page": 1, "page_size": 5}
        )
        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["first_name"] == "Ana03"

    def test_invalid_page_size_returns_400(self, staff_client, users):
        resp = staff_client.get(reverse("users:users"), {"page_size": "abc"})
        assert resp.status_code == 400
