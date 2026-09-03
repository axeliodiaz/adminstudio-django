import pytest
from django.urls import reverse
from rest_framework import status

from apps.docs.models import DocAudience, DocPage, DocSection
from apps.docs.sanitize import sanitize_html


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

    def test_seeded_feature_guides_are_public(self, api_client):
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
        assert {
            "admin-dashboard",
            "admin-horarios",
            "admin-reservas",
            "asistencia",
            "admin-socios",
        }.issubset(sections["operacion-admin"])
        assert {
            "billeteras-y-compras",
            "gestionar-planes-y-beneficios",
            "gestionar-codigos-promocionales",
        }.issubset(sections["comercial-admin"])

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

    def test_list_can_filter_by_audience(self, api_client, published_page):
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

        response = api_client.get(reverse("docs-list"), {"audience": "coach"})

        assert response.status_code == status.HTTP_200_OK
        assert [group["id"] for group in response.data["audiences"]] == ["coach"]

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
