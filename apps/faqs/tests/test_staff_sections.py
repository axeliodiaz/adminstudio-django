"""Staff-only FAQ sections (CYC-420)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.faqs.models import FAQItem, Section

User = get_user_model()


@pytest.fixture
def staff_section(db):
    section = Section.objects.create(
        name="Comunicaciones",
        slug="comunicaciones-staff",
        order=90,
        requires_staff=True,
    )
    FAQItem.objects.create(
        section=section, question="¿Cómo filtro?", answer="Con condiciones.", order=1
    )
    return section


@pytest.fixture
def public_section(db):
    section = Section.objects.create(name="Horarios", slug="horarios", order=1)
    FAQItem.objects.create(
        section=section, question="¿Cuándo hay clases?", answer="De mañana.", order=1
    )
    return section


def _authed_client(api_client, **user_kwargs):
    user = User.objects.create_user(password="testpass123", **user_kwargs)
    token = ExpiringToken.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestStaffOnlySections:
    def test_anonymous_does_not_see_staff_section(self, api_client, staff_section, public_section):
        response = api_client.get(reverse("faqs-list"))
        assert response.status_code == status.HTTP_200_OK
        names = [s["name"] for s in response.data["sections"]]
        assert names == ["Horarios"]

    def test_member_does_not_see_staff_section(self, api_client, staff_section, public_section):
        client = _authed_client(api_client, username="faq.member")
        response = client.get(reverse("faqs-list"))
        names = [s["name"] for s in response.data["sections"]]
        assert names == ["Horarios"]

    def test_staff_sees_staff_section(self, api_client, staff_section, public_section):
        client = _authed_client(api_client, username="faq.admin", is_staff=True)
        response = client.get(reverse("faqs-list"))
        names = [s["name"] for s in response.data["sections"]]
        assert names == ["Horarios", "Comunicaciones"]
        staff_rows = [s for s in response.data["sections"] if s["name"] == "Comunicaciones"]
        assert staff_rows[0]["requires_staff"] is True

    def test_admin_section_schema_exposes_flag(self, api_client, staff_section):
        client = _authed_client(api_client, username="faq.super", is_staff=True, is_superuser=True)
        response = client.get(reverse("admin-faq-section-list"))
        assert response.status_code == status.HTTP_200_OK
        row = [s for s in response.data if s["slug"] == "comunicaciones-staff"][0]
        assert row["requires_staff"] is True

    def test_superuser_can_toggle_flag(self, api_client, public_section):
        client = _authed_client(api_client, username="faq.super2", is_staff=True, is_superuser=True)
        response = client.patch(
            reverse("admin-faq-section-detail", args=[public_section.id]),
            {"requires_staff": True},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["requires_staff"] is True


@pytest.mark.django_db
class TestSeedCommand:
    def test_seed_is_idempotent(self):
        from django.core.management import call_command

        call_command("seed_communications_faq", verbosity=0)
        section = Section.objects.get(slug="comunicaciones-staff")
        assert section.requires_staff is True
        assert FAQItem.objects.filter(section=section).count() == 5
        call_command("seed_communications_faq", verbosity=0)
        assert FAQItem.objects.filter(section=section).count() == 5
