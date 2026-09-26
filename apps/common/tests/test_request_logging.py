import logging
import re

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from apps.common.middleware import (
    SentryRequestUrlMiddleware,
    redact_querystring,
    request_url_for_log,
    should_log_request_path,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/members/", True),
        ("/admin/", True),
        ("/api/healthcheck/", False),
        ("/api/healthcheck", False),
        ("/static/admin/css/base.css", False),
        ("/media/profiles/a.png", False),
        ("/favicon.ico", False),
    ],
)
def test_should_log_request_path(path, expected):
    assert should_log_request_path(path) is expected


def test_redact_querystring_strips_secrets():
    assert redact_querystring("token=abc&foo=1") == "token=***&foo=1"
    assert redact_querystring("") == ""


def test_request_url_for_log_includes_redacted_query():
    request = RequestFactory().get("/api/members/?token=secret&studio=1")
    url = request_url_for_log(request)
    assert url.startswith("/api/members/?")
    assert "secret" not in url
    assert "studio=1" in url


def test_middleware_logs_method_url_and_status(caplog):
    caplog.set_level(logging.INFO, logger="apps.common.request")

    def get_response(request):
        return HttpResponse("ok", status=201)

    middleware = SentryRequestUrlMiddleware(get_response)
    request = RequestFactory().post("/api/members/")
    response = middleware(request)

    assert response.status_code == 201
    assert "HTTP POST /api/members/ 201" in caplog.text


def test_middleware_skips_healthcheck(caplog):
    caplog.set_level(logging.INFO, logger="apps.common.request")

    def get_response(request):
        return HttpResponse("ok")

    middleware = SentryRequestUrlMiddleware(get_response)
    middleware(RequestFactory().get("/api/healthcheck/"))

    assert caplog.text == ""


def test_middleware_logs_500_when_view_raises(caplog):
    caplog.set_level(logging.INFO, logger="apps.common.request")

    def get_response(request):
        raise RuntimeError("boom")

    middleware = SentryRequestUrlMiddleware(get_response)
    with pytest.raises(RuntimeError):
        middleware(RequestFactory().get("/api/coach/"))

    assert "HTTP GET /api/coach/ 500" in caplog.text


@override_settings(
    ROOT_URLCONF="adminstudio_django.urls",
)
@pytest.mark.django_db
def test_live_request_logs_url(client, caplog):
    caplog.set_level(logging.INFO, logger="apps.common.request")
    client.get("/api/healthcheck/")
    assert "HTTP GET /api/healthcheck/" not in caplog.text
    client.get("/api/does-not-exist/")
    assert "HTTP GET /api/does-not-exist/ 404" in caplog.text



def test_middleware_logs_duration_ms(caplog):
    caplog.set_level(logging.INFO, logger="apps.common.request")

    def get_response(request):
        return HttpResponse("ok")

    middleware = SentryRequestUrlMiddleware(get_response)
    middleware(RequestFactory().get("/api/members/"))

    assert re.search(r"HTTP GET /api/members/ 200 \d+ms", caplog.text)


def test_middleware_duration_structured_extra(caplog):
    caplog.set_level(logging.INFO, logger="apps.common.request")

    def get_response(request):
        return HttpResponse("ok")

    middleware = SentryRequestUrlMiddleware(get_response)
    with caplog.at_level(logging.INFO, logger="apps.common.request"):
        middleware(RequestFactory().get("/api/members/"))

    record = next(r for r in caplog.records if r.name == "apps.common.request")
    assert isinstance(record.http_duration_ms, float)
    assert record.http_duration_ms >= 0


def test_apps_logger_does_not_duplicate_emission():
    """CYC-109: the 'apps' logger must propagate to root only; its own
    console handler used to emit every line a second time."""
    from django.conf import settings

    apps_logger = settings.LOGGING["loggers"]["apps"]
    assert apps_logger.get("propagate", True) is True
    assert not apps_logger.get("handlers")
