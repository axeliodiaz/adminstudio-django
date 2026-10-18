import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.studios.branding import DEFAULT_BRANDING, BrandingError, sanitize_svg
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
