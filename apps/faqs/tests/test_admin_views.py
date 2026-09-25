"""API tests for staff admin FAQ endpoints."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.faqs.models import FAQItem, Section

User = get_user_model()


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="adminuser",
        email="admin@example.com",
        password="pass1234",
        is_staff=True,
    )


@pytest.fixture
def staff_client(api_client, staff_user):
    token = ExpiringToken.objects.create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def superuser():
    return User.objects.create_superuser(
        username="superadmin",
        email="superadmin@example.com",
        password="pass1234",
    )


@pytest.fixture
def superuser_client(api_client, superuser):
    token = ExpiringToken.objects.create(user=superuser)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def section():
    return Section.objects.create(
        name="Reservas",
        slug="reservas",
        description="Cómo reservar",
        order=1,
    )


@pytest.mark.django_db
class TestPublicFAQView:
    def test_public_list_omits_unpublished_items(self, api_client, section):
        FAQItem.objects.create(
            section=section,
            question="¿Cómo cancelo?",
            answer="Desde **Mis reservas**.",
            order=1,
            is_published=True,
        )
        FAQItem.objects.create(
            section=section,
            question="Borrador",
            answer="No sale.",
            order=2,
            is_published=False,
        )

        response = api_client.get(reverse("faqs-list"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["sections"]) == 1
        questions = [item["question"] for item in response.data["sections"][0]["items"]]
        assert questions == ["¿Cómo cancelo?"]


@pytest.mark.django_db
class TestAdminFAQSectionViews:
    def test_list_requires_staff(self, api_client):
        user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="pass1234",
        )
        token = ExpiringToken.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("admin-faq-section-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_and_update_section(self, superuser_client):
        create_response = superuser_client.post(
            reverse("admin-faq-section-list"),
            data={"name": "Membresías", "description": "Planes y pagos"},
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        section_id = create_response.data["id"]
        assert create_response.data["name"] == "Membresías"
        assert create_response.data["slug"] == "membresias"

        update_response = superuser_client.patch(
            reverse("admin-faq-section-detail", kwargs={"section_id": section_id}),
            data={"name": "Membresías y planes", "order": 3},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["name"] == "Membresías y planes"
        assert update_response.data["order"] == 3

    def test_create_section_requires_name(self, superuser_client):
        response = superuser_client.post(
            reverse("admin-faq-section-list"),
            data={"description": "Sin nombre"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Section.objects.count() == 0


@pytest.mark.django_db
class TestAdminFAQItemViews:
    def test_create_and_update_item(self, superuser_client, section):
        create_response = superuser_client.post(
            reverse("admin-faq-item-list"),
            data={
                "section_id": str(section.id),
                "question": "¿Cómo cancelo una reserva?",
                "answer": "Puedes cancelar desde **Mis reservas**.",
                "is_published": True,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        item_id = create_response.data["id"]
        assert create_response.data["section_id"] == str(section.id)
        assert create_response.data["is_published"] is True

        update_response = superuser_client.patch(
            reverse("admin-faq-item-detail", kwargs={"item_id": item_id}),
            data={"is_published": False, "order": 4},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["is_published"] is False
        assert update_response.data["order"] == 4
        assert FAQItem.objects.get(id=item_id).is_published is False

    def test_list_filters_by_status_and_search(self, superuser_client, section):
        FAQItem.objects.create(
            section=section,
            question="¿Cómo cancelo?",
            answer="Desde la app.",
            is_published=True,
        )
        FAQItem.objects.create(
            section=section,
            question="Pregunta borrador",
            answer="Todavía no.",
            is_published=False,
        )

        published = superuser_client.get(reverse("admin-faq-item-list"), {"status": "published"})
        assert published.status_code == status.HTTP_200_OK
        assert all(row["is_published"] is True for row in published.data)

        search = superuser_client.get(reverse("admin-faq-item-list"), {"search": "borrador"})
        assert search.status_code == status.HTTP_200_OK
        assert [row["question"] for row in search.data] == ["Pregunta borrador"]

    def test_create_item_requires_question(self, superuser_client, section):
        response = superuser_client.post(
            reverse("admin-faq-item-list"),
            data={"section_id": str(section.id), "answer": "Sin pregunta"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert FAQItem.objects.count() == 0


@pytest.mark.django_db
class TestAdminFAQWritePermissions:
    """CYC-120: writes are superuser-only; staff read published items only."""

    def test_staff_cannot_create_section(self, staff_client):
        response = staff_client.post(
            reverse("admin-faq-section-list"),
            data={"name": "No permitido"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Section.objects.count() == 0

    def test_staff_cannot_update_section(self, staff_client, section):
        response = staff_client.patch(
            reverse("admin-faq-section-detail", kwargs={"section_id": section.id}),
            data={"name": "No permitido"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        section.refresh_from_db()
        assert section.name != "No permitido"

    def test_staff_cannot_create_item(self, staff_client, section):
        response = staff_client.post(
            reverse("admin-faq-item-list"),
            data={"section_id": str(section.id), "question": "¿X?", "answer": "Y"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert FAQItem.objects.count() == 0

    def test_staff_list_only_shows_published(self, staff_client, section):
        FAQItem.objects.create(
            section=section,
            question="Publicada",
            answer="Sí.",
            is_published=True,
        )
        FAQItem.objects.create(
            section=section,
            question="Borrador oculto",
            answer="No.",
            is_published=False,
        )

        default = staff_client.get(reverse("admin-faq-item-list"))
        assert [row["question"] for row in default.data] == ["Publicada"]

        draft_filter = staff_client.get(reverse("admin-faq-item-list"), {"status": "draft"})
        assert [row["question"] for row in draft_filter.data] == ["Publicada"]

        search = staff_client.get(reverse("admin-faq-item-list"), {"search": "Borrador"})
        assert search.status_code == status.HTTP_200_OK
        assert search.data == []

    def test_staff_cannot_read_draft_detail(self, staff_client, section):
        item = FAQItem.objects.create(
            section=section,
            question="Borrador",
            answer="No.",
            is_published=False,
        )
        response = staff_client.get(reverse("admin-faq-item-detail", kwargs={"item_id": item.id}))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_superuser_can_read_draft_detail(self, superuser_client, section):
        item = FAQItem.objects.create(
            section=section,
            question="Borrador",
            answer="No.",
            is_published=False,
        )
        response = superuser_client.get(
            reverse("admin-faq-item-detail", kwargs={"item_id": item.id})
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_published"] is False
