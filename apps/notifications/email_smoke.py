"""Temporary fixed-content owner-only deployment verification. Remove after use."""

import hashlib
import hmac
import time

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.notifications.mailing import Email

DIGEST = "65640964c2a7202751fea58f92d829c774727db93870e40faace4874df0e3589"
EXPIRES = 1795750442


@csrf_exempt
@require_POST
def email_smoke(request):
    if time.time() >= EXPIRES:
        return JsonResponse({"detail": "Not found"}, status=404)
    supplied = request.headers.get("Authorization", "")
    digest = hashlib.sha256(supplied.removeprefix("Bearer ").encode()).hexdigest()
    if not hmac.compare_digest(digest, DIGEST):
        return JsonResponse({"detail": "Not found"}, status=404)
    email = Email(
        notification_id="",
        subject="Prueba de correo: Admin Studio",
        message="Este correo confirma el envío desde la aplicación mediante Cloudflare. No requiere ninguna acción.",
        recipient_list=["diaz.axelio@gmail.com"],
    )
    if not email._cloudflare_is_configured():
        return JsonResponse({"detail": "Cloudflare configuration unavailable"}, status=503)
    # Production uses DatabaseCache: add claims a unique key across workers/restarts.
    try:
        claimed = cache.add("email-smoke:" + DIGEST, "claimed", timeout=86400)
    except Exception:
        return JsonResponse({"detail": "Durable claim storage unavailable"}, status=503)
    if not claimed:
        return JsonResponse(
            {"detail": "Already attempted; inspect delivery before any retry"}, status=409
        )
    try:
        email._send_via_cloudflare()
    except Exception:
        return JsonResponse({"detail": "Send not confirmed; do not retry"}, status=502)
    return JsonResponse({"accepted": True})
