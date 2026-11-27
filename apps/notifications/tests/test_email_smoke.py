import hashlib
from unittest.mock import MagicMock, patch

from django.test import RequestFactory

from apps.notifications import email_smoke as smoke


def test_smoke_auth_expiry_and_durable_claim(monkeypatch):
    monkeypatch.setattr(smoke, "DIGEST", hashlib.sha256(b"test-only").hexdigest())
    monkeypatch.setattr(smoke, "EXPIRES", 9999999999)
    factory = RequestFactory()
    assert smoke.email_smoke(factory.post("/")).status_code == 404
    request = factory.post("/", HTTP_AUTHORIZATION="Bearer test-only")
    email = MagicMock()
    email._cloudflare_is_configured.return_value = True
    with (
        patch.object(smoke, "Email", return_value=email) as constructor,
        patch.object(smoke.cache, "add", side_effect=[True, False]),
    ):
        assert smoke.email_smoke(request).status_code == 200
        assert smoke.email_smoke(request).status_code == 409
    assert constructor.call_args.kwargs["recipient_list"] == ["diaz.axelio@gmail.com"]
    assert constructor.call_args.kwargs["subject"] == "Prueba de correo: Admin Studio"
    email._send_via_cloudflare.assert_called_once()
    monkeypatch.setattr(smoke, "EXPIRES", 0)
    assert smoke.email_smoke(request).status_code == 404


def test_smoke_fail_closed_on_claim_error(monkeypatch):
    monkeypatch.setattr(smoke, "DIGEST", hashlib.sha256(b"test-only").hexdigest())
    monkeypatch.setattr(smoke, "EXPIRES", 9999999999)
    email = MagicMock()
    email._cloudflare_is_configured.return_value = True
    request = RequestFactory().post("/", HTTP_AUTHORIZATION="Bearer test-only")
    with (
        patch.object(smoke, "Email", return_value=email),
        patch.object(smoke.cache, "add", side_effect=RuntimeError),
    ):
        assert smoke.email_smoke(request).status_code == 503
    email._send_via_cloudflare.assert_not_called()
