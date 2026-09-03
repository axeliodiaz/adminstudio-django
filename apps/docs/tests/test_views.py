import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status
from rest_framework.test import APIClient

from apps.docs.models import DocAudience, DocPage, DocSection
from apps.docs.sanitize import sanitize_html
from apps.instructors.models import Instructor

User = get_user_model()


@pytest.fixture
def published_section():
    return DocSection.objects.create(
        audience=DocAudience.MEMBER,
        title="Clases",
        slug="clases",
        order=1,
        is_published=True,
    )


@pytest.fixture
def published_page(published_section):
    return DocPage.objects.create(
        section=published_section,
        title="Cómo reservar",
        slug="como-reservar",
        summary="Reserva un spot desde el calendario.",
        body='<h2>Reservar</h2><p>Abre <a href="#classes">Clases</a>.</p>',
        order=1,
        is_published=True,
        related_app_route="#classes",
    )


@pytest.fixture
def staff_client():
    user = User.objects.create_user(
        username="docsadmin",
        email="docsadmin@example.com",
        password="pass1234",
        is_staff=True,
    )
    token = ExpiringToken.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def coach_client():
    user = User.objects.create_user(
        username="docscoach",
        email="docscoach@example.com",
        password="pass1234",
    )
    Instructor.objects.create(user=user)
    token = ExpiringToken.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.mark.django_db
class TestSanitizeHtml:
    def test_strips_script_and_keeps_safe_markup(self):
        html = '<p>Hola</p><script>alert(1)</script><a href="javascript:alert(1)">x</a>'
        cleaned = sanitize_html(html)
        assert "<script>" not in cleaned
        assert "javascript:" not in cleaned
        assert "<p>Hola</p>" in cleaned

    def test_page_save_sanitizes_body(self, published_section):
        page = DocPage.objects.create(
            section=published_section,
            title="XSS",
            slug="xss",
            body='<p>ok</p><img src=x onerror="alert(1)">',
            is_published=True,
        )
        page.refresh_from_db()
        assert "onerror" not in page.body
        assert "<p>ok</p>" in page.body


@pytest.mark.django_db
class TestPublicDocsAPI:
    def test_seeded_classes_guide_is_public(self, api_client):
        response = api_client.get(
            reverse(
                "docs-detail",
                kwargs={
                    "section_slug": "clases-y-horarios",
                    "page_slug": "como-ver-clases-y-horarios",
                },
            )
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["related_app_route"] == "#classes"
        assert "Reserva tu spot" in response.data["body"]

    def test_seeded_class_reservation_guide_is_public(self, api_client):
        response = api_client.get(
            reverse(
                "docs-detail",
                kwargs={
                    "section_slug": "clases-y-horarios",
                    "page_slug": "como-reservar-una-clase",
                },
            )
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["related_app_route"] == "#classes"
        assert "Confirmar reserva" in response.data["body"]
        assert "lista de espera" in response.data["body"]

    def test_public_list_omits_admin_and_coach_guides(self, api_client):
        response = api_client.get(reverse("docs-list"))

        assert response.status_code == status.HTTP_200_OK
        sections = {
            section["slug"]: {page["slug"] for page in section["pages"]}
            for audience in response.data["audiences"]
            for section in audience["sections"]
        }
        assert {
            "como-explorar-instructores",
            "preguntas-frecuentes-publicas",
            "documentos-legales",
        }.issubset(sections["informacion-publica"])
        assert {
            "como-elegir-planes-y-membresias",
            "carrito-de-compras",
            "checkout-y-codigos-promocionales",
            "tu-billetera",
        }.issubset(sections["planes-y-compras"])
        assert {
            "mi-perfil",
            "cuenta-y-autenticacion",
            "mis-reservas",
            "lista-de-espera",
            "cancelaciones",
            "mis-estadisticas",
        }.issubset(sections["mi-cuenta"])
        assert {"emails-transaccionales", "cola-de-notificaciones"}.issubset(sections["plataforma"])
        assert "operacion-admin" not in sections
        assert "panel-coach" not in sections

    def test_staff_list_includes_admin_guides_but_not_coach_guides(self, staff_client):
        response = staff_client.get(reverse("docs-list"))

        assert response.status_code == status.HTTP_200_OK
        sections = {
            section["slug"]: {page["slug"] for page in section["pages"]}
            for audience in response.data["audiences"]
            for section in audience["sections"]
        }
        assert {"admin-dashboard", "admin-horarios", "admin-reservas"}.issubset(
            sections["operacion-admin"]
        )
        assert "panel-coach" not in sections

    def test_coach_list_includes_coach_guides_but_not_admin_guides(self, coach_client):
        response = coach_client.get(reverse("docs-list"))

        assert response.status_code == status.HTTP_200_OK
        sections = {
            section["slug"]: {page["slug"] for page in section["pages"]}
            for audience in response.data["audiences"]
            for section in audience["sections"]
        }
        assert {"coach-clases-del-dia", "coach-roster-check-in"}.issubset(sections["panel-coach"])
        assert "operacion-admin" not in sections

    def test_list_omits_unpublished_pages_and_empty_sections(self, api_client, published_section):
        DocPage.objects.create(
            section=published_section,
            title="Visible",
            slug="visible",
            summary="Sí",
            body="<p>Publicado</p>",
            is_published=True,
        )
        DocPage.objects.create(
            section=published_section,
            title="Borrador",
            slug="borrador",
            summary="No",
            body="<p>Draft</p>",
            is_published=False,
        )
        draft_section = DocSection.objects.create(
            audience=DocAudience.ADMIN,
            title="Admin interno",
            slug="admin-interno",
            is_published=False,
        )
        DocPage.objects.create(
            section=draft_section,
            title="No sale",
            slug="no-sale",
            body="<p>x</p>",
            is_published=True,
        )
        empty_section = DocSection.objects.create(
            audience=DocAudience.MEMBER,
            title="Vacía",
            slug="vacia",
            is_published=True,
        )
        DocPage.objects.create(
            section=empty_section,
            title="Solo draft",
            slug="solo-draft",
            body="<p>x</p>",
            is_published=False,
        )

        response = api_client.get(reverse("docs-list"), {"audience": "member"})

        assert response.status_code == status.HTTP_200_OK
        audiences = response.data["audiences"]
        assert [group["id"] for group in audiences] == ["member"]
        sections = audiences[0]["sections"]
        section = next(item for item in sections if item["slug"] == "clases")
        assert "vacia" not in [item["slug"] for item in sections]
        slugs = [page["slug"] for page in section["pages"]]
        assert slugs == ["visible"]
        assert "body" not in section["pages"][0]

    def test_coach_can_filter_by_coach_audience(self, coach_client, published_page):
        coach_section = DocSection.objects.create(
            audience=DocAudience.COACH,
            title="Coach",
            slug="coach",
            is_published=True,
        )
        DocPage.objects.create(
            section=coach_section,
            title="Roster",
            slug="roster",
            body="<p>Lista</p>",
            is_published=True,
        )

        response = coach_client.get(reverse("docs-list"), {"audience": "coach"})

        assert response.status_code == status.HTTP_200_OK
        assert [group["id"] for group in response.data["audiences"]] == ["coach"]

    def test_protected_page_is_only_visible_to_matching_audience(
        self, api_client, staff_client, coach_client
    ):
        admin_section = DocSection.objects.create(
            audience=DocAudience.ADMIN,
            title="Admin protegido",
            slug="admin-protegido",
            is_published=True,
        )
        coach_section = DocSection.objects.create(
            audience=DocAudience.COACH,
            title="Coach protegido",
            slug="coach-protegido",
            is_published=True,
        )
        DocPage.objects.create(
            section=admin_section,
            title="Admin",
            slug="admin",
            body="<p>Solo staff</p>",
            is_published=True,
        )
        DocPage.objects.create(
            section=coach_section,
            title="Coach",
            slug="coach",
            body="<p>Solo coaches</p>",
            is_published=True,
        )
        admin_url = reverse(
            "docs-detail",
            kwargs={"section_slug": "admin-protegido", "page_slug": "admin"},
        )
        coach_url = reverse(
            "docs-detail",
            kwargs={"section_slug": "coach-protegido", "page_slug": "coach"},
        )

        assert api_client.get(admin_url).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.get(coach_url).status_code == status.HTTP_404_NOT_FOUND
        assert staff_client.get(admin_url).status_code == status.HTTP_200_OK
        assert staff_client.get(coach_url).status_code == status.HTTP_404_NOT_FOUND
        assert coach_client.get(admin_url).status_code == status.HTTP_404_NOT_FOUND
        assert coach_client.get(coach_url).status_code == status.HTTP_200_OK

    def test_list_rejects_unknown_audience(self, api_client):
        response = api_client.get(reverse("docs-list"), {"audience": "guest"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_detail_returns_published_page(self, api_client, published_page):
        url = reverse(
            "docs-detail",
            kwargs={"section_slug": "clases", "page_slug": "como-reservar"},
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Cómo reservar"
        assert "Reservar" in response.data["body"]
        assert response.data["section"]["slug"] == "clases"
        assert response.data["related_app_route"] == "#classes"

    def test_detail_404_for_draft_page(self, api_client, published_section):
        DocPage.objects.create(
            section=published_section,
            title="Draft",
            slug="draft",
            body="<p>no</p>",
            is_published=False,
        )
        url = reverse("docs-detail", kwargs={"section_slug": "clases", "page_slug": "draft"})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_404_when_section_is_unpublished(self, api_client):
        section = DocSection.objects.create(
            audience=DocAudience.MEMBER,
            title="Oculta",
            slug="oculta",
            is_published=False,
        )
        DocPage.objects.create(
            section=section,
            title="Artículo",
            slug="articulo",
            body="<p>no</p>",
            is_published=True,
        )
        url = reverse("docs-detail", kwargs={"section_slug": "oculta", "page_slug": "articulo"})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
