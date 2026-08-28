import logging
from urllib.parse import parse_qsl, urlencode

logger = logging.getLogger("apps.common.request")

SKIP_PATH_PREFIXES = (
    "/api/healthcheck",
    "/static/",
    "/media/",
    "/favicon.ico",
)

REDACT_QUERY_KEYS = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "password",
        "secret",
        "api_key",
        "apikey",
        "key",
        "authorization",
        "auth",
    }
)


def should_log_request_path(path: str) -> bool:
    return not any(path.startswith(prefix) for prefix in SKIP_PATH_PREFIXES)


def redact_querystring(query_string: str) -> str:
    if not query_string:
        return ""
    pairs = []
    for key, value in parse_qsl(query_string, keep_blank_values=True):
        if key.lower() in REDACT_QUERY_KEYS:
            pairs.append((key, "***"))
        else:
            pairs.append((key, value))
    return urlencode(pairs, safe="*")


def request_url_for_log(request) -> str:
    path = request.path
    query = redact_querystring(request.META.get("QUERY_STRING", ""))
    if query:
        return f"{path}?{query}"
    return path


class SentryRequestUrlMiddleware:
    """Log every incoming HTTP URL at INFO so Sentry Logs (not Issues) receive them."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Exception:
            self._log(request, status_code=500)
            raise
        self._log(request, status_code=response.status_code)
        return response

    def _log(self, request, status_code: int) -> None:
        path = request.path
        if not should_log_request_path(path):
            return
        url = request_url_for_log(request)
        logger.info(
            "HTTP %s %s %s",
            request.method,
            url,
            status_code,
            extra={
                "http_method": request.method,
                "http_path": path,
                "http_status_code": status_code,
            },
        )
