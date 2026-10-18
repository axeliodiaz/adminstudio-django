import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.studios.branding import DEFAULT_BRANDING, BrandingError, sanitize_svg
from model_bakery import baker

from apps.studios.models import StudioBranding

User = get_user_model()

GOOD_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<circle cx="5" cy="5" r="4" fill="#4F46E5"/></svg>'
)


def _auth(api_client, user):
    token = ExpiringToken.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


@pytest.fixture
def superuser():
    return User.objects.create_superuser(
        username="brand_super", email="brand_super@ex.com", password="pass"
    )


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="brand_staff",
        email="brand_staff@ex.com",
        password="pass",
        is_staff=True,
    )


class TestSanitizeSvg:
    def test_keeps_safe_shapes(self):
        out = sanitize_svg(GOOD_SVG)
        assert "<circle" in out and 'viewBox="0 0 10 10"' in out

    def test_empty_means_no_logo(self):
        assert sanitize_svg("   ") == ""

    @pytest.mark.parametrize(
        "payload",
        [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><script>x()</script></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><foreignObject/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><image href="http://e/x.png"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><style>a{}</style></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><a href="http://e"/></svg>',
            '<!DOCTYPE svg [<!ENTITY a "b">]><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>',
            "<html><body/></html>",
            "not xml at all",
            '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>',
        ],
    )
    def test_rejects_dangerous_or_invalid(self, payload):
        with pytest.raises(BrandingError):
            sanitize_svg(payload)

    def test_rejects_oversized(self):
        big = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            + ("<g/>" * 30000)
            + "</svg>"
        )
        with pytest.raises(BrandingError):
            sanitize_svg(big)

    def test_strips_handlers_external_refs_and_unsafe_styles(self):
        dirty = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1" onload="x()">'
            '<path d="M0 0h1" onclick="x()" fill="url(http://e/x)" '
            'style="fill:red;behavior:url(x);stroke:url(http://e/y)"/>'
            '<use href="http://e/x#a"/></svg>'
        )
        out = sanitize_svg(dirty)
        for fragment in ("onload", "onclick", "http://e", "behavior", "javascript"):
            assert fragment not in out
        assert 'style="fill:red"' in out


@pytest.mark.django_db
class TestPublicBranding:
    def test_anonymous_gets_defaults_without_logo_secrets(self, api_client):
        response = api_client.get(reverse("studio-branding"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["primary_color"] == DEFAULT_BRANDING["primary_color"]
        assert response.data["primary_color"] != "#C9A66B"
        assert "options" not in response.data

    def test_anonymous_cannot_write(self, api_client):
        response = api_client.patch(reverse("studio-branding"), {"name": "X"}, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestAdminBranding:
    def test_anonymous_gets_401(self, api_client):
        assert (
            api_client.get(reverse("admin-studio-branding")).status_code
            == status.HTTP_401_UNAUTHORIZED
        )

    def test_plain_staff_gets_403_on_every_method(self, api_client, staff_user):
        _auth(api_client, staff_user)
        url = reverse("admin-studio-branding")
        assert api_client.get(url).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.patch(url, {"name": "X"}, format="json").status_code == 403
        assert api_client.post(reverse("admin-studio-branding-reset")).status_code == 403
        assert StudioBranding.load().name == DEFAULT_BRANDING["name"]

    def test_superuser_reads_with_options(self, api_client, superuser):
        _auth(api_client, superuser)
        response = api_client.get(reverse("admin-studio-branding"))
        assert response.status_code == status.HTTP_200_OK
        assert "Rubik" in response.data["options"]["fonts"]

    def test_superuser_updates_and_public_reflects(self, api_client, superuser):
        _auth(api_client, superuser)
        response = api_client.patch(
            reverse("admin-studio-branding"),
            {
                "name": "Ritmo Studio",
                "primary_color": "#0d9488",
                "heading_font": "Poppins",
                "logo_svg": GOOD_SVG,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["primary_color"] == "#0D9488"
        api_client.credentials()
        public = api_client.get(reverse("studio-branding")).data
        assert public["name"] == "Ritmo Studio"
        assert public["heading_font"] == "Poppins"
        assert "<circle" in public["logo_svg"]

    @pytest.mark.parametrize(
        "payload",
        [
            {"primary_color": "red"},
            {"primary_color": "#12345"},
            {"text_color": "url(javascript:1)"},
            {"heading_font": "Comic Sans; } body { display:none"},
            {"name": ""},
            {"name": "<script>"},
            {"logo_svg": "<svg><script/></svg>"},
        ],
    )
    def test_invalid_payload_is_rejected_and_not_saved(self, api_client, superuser, payload):
        _auth(api_client, superuser)
        response = api_client.patch(reverse("admin-studio-branding"), payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert StudioBranding.load().primary_color == DEFAULT_BRANDING["primary_color"]

    def test_empty_logo_removes_it(self, api_client, superuser):
        _auth(api_client, superuser)
        url = reverse("admin-studio-branding")
        api_client.patch(url, {"logo_svg": GOOD_SVG}, format="json")
        response = api_client.patch(url, {"logo_svg": ""}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["logo_svg"] == ""

    def test_reset_restores_defaults(self, api_client, superuser):
        _auth(api_client, superuser)
        api_client.patch(
            reverse("admin-studio-branding"),
            {"name": "Otro", "primary_color": "#000000"},
            format="json",
        )
        response = api_client.post(reverse("admin-studio-branding-reset"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == DEFAULT_BRANDING["name"]
        assert response.data["primary_color"] == DEFAULT_BRANDING["primary_color"]


@pytest.mark.django_db
class TestPerStudioBranding:
    def test_studio_override_does_not_change_default(self, api_client, superuser):
        studio = baker.make("studios.Studio", name="Sede Norte")
        _auth(api_client, superuser)
        url = reverse("admin-studio-branding")
        response = api_client.patch(
            f"{url}?studio={studio.id}", {"primary_color": "#0D9488"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["studio_id"] == str(studio.id)
        assert StudioBranding.load().primary_color == DEFAULT_BRANDING["primary_color"]
        api_client.credentials()
        public_url = reverse("studio-branding")
        assert api_client.get(f"{public_url}?studio={studio.id}").data["primary_color"] == "#0D9488"
        assert api_client.get(public_url).data["primary_color"] == DEFAULT_BRANDING["primary_color"]

    def test_studio_without_row_falls_back_to_default(self, api_client):
        studio = baker.make("studios.Studio", name="Sede Sur")
        data = api_client.get(f"{reverse('studio-branding')}?studio={studio.id}").data
        assert data["studio_id"] is None
        assert data["primary_color"] == DEFAULT_BRANDING["primary_color"]

    def test_unknown_or_malformed_studio_is_404(self, api_client, superuser):
        public = reverse("studio-branding")
        assert api_client.get(f"{public}?studio=nope").status_code == status.HTTP_404_NOT_FOUND
        _auth(api_client, superuser)
        admin_url = reverse("admin-studio-branding")
        missing = "00000000-0000-0000-0000-000000000000"
        assert api_client.get(f"{admin_url}?studio={missing}").status_code == 404

    def test_plain_staff_cannot_edit_a_studio_row(self, api_client, staff_user):
        studio = baker.make("studios.Studio", name="Sede Este")
        _auth(api_client, staff_user)
        url = f"{reverse('admin-studio-branding')}?studio={studio.id}"
        assert api_client.patch(url, {"name": "X"}, format="json").status_code == 403
        assert not StudioBranding.objects.filter(studio=studio).exists()

    def test_reset_studio_drops_override(self, api_client, superuser):
        studio = baker.make("studios.Studio", name="Sede Oeste")
        _auth(api_client, superuser)
        url = f"{reverse('admin-studio-branding')}?studio={studio.id}"
        api_client.patch(url, {"name": "Custom"}, format="json")
        response = api_client.post(f"{reverse('admin-studio-branding-reset')}?studio={studio.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["studio_id"] is None
        assert not StudioBranding.objects.filter(studio=studio).exists()


@pytest.mark.django_db
class TestSingleActiveStudioResolution:
    """Exactly one active studio: the site and Marca use that studio's row."""

    def test_public_uses_the_single_active_studio_row(self, api_client):
        studio = baker.make("studios.Studio", name="Sede Unica", is_active=True)
        StudioBranding.objects.create(studio=studio, name=studio.name, primary_color="#C9A66B")
        data = api_client.get(reverse("studio-branding")).data
        assert data["studio_id"] == str(studio.id)
        assert data["primary_color"] == "#C9A66B"

    def test_admin_without_param_edits_the_studio_row(self, api_client, superuser):
        studio = baker.make("studios.Studio", name="Sede Unica", is_active=True)
        _auth(api_client, superuser)
        response = api_client.patch(
            reverse("admin-studio-branding"), {"primary_color": "#C9A66B"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["studio_id"] == str(studio.id)
        assert StudioBranding.load().primary_color == DEFAULT_BRANDING["primary_color"]
        assert StudioBranding.load(studio).primary_color == "#C9A66B"

    def test_active_studio_without_row_gets_default_palette(self, api_client):
        baker.make("studios.Studio", name="Sede Nueva", is_active=True)
        data = api_client.get(reverse("studio-branding")).data
        assert data["studio_id"] is None
        assert data["primary_color"] == DEFAULT_BRANDING["primary_color"]

    def test_two_active_studios_use_the_default_row(self, api_client):
        baker.make("studios.Studio", is_active=True)
        baker.make("studios.Studio", is_active=True)
        data = api_client.get(reverse("studio-branding")).data
        assert data["studio_id"] is None
        assert data["primary_color"] == DEFAULT_BRANDING["primary_color"]
