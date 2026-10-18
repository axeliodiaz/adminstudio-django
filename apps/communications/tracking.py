"""Click tracking service (CYC-396)."""

import hashlib

from django.db.models import F
from django.utils import timezone

from apps.communications.models import TrackedLink, TrackedLinkClick

ALLOWED_SCHEMES = ("http", "https")


def validate_target_url(target_url):
    """Only absolute http(s) URLs can be tracked."""
    if not isinstance(target_url, str) or not target_url.strip():
        raise ValueError("'target_url' is required.")
    target_url = target_url.strip()
    scheme = target_url.split("://", 1)[0].lower()
    if "://" not in target_url or scheme not in ALLOWED_SCHEMES:
        raise ValueError("'target_url' must be an absolute http(s) URL.")
    if len(target_url) > 1000:
        raise ValueError("'target_url' is too long (max 1000 chars).")
    return target_url


def _hash_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded_for.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
    if not ip:
        return ""
    return hashlib.sha256(ip.encode()).hexdigest()


def record_click(link, request):
    """Record a click and keep the precomputed aggregates on the link fresh."""
    TrackedLinkClick.objects.create(
        link=link,
        user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:300],
        ip_hash=_hash_ip(request),
    )
    now = timezone.now()
    TrackedLink.objects.filter(pk=link.pk).update(
        click_count=F("click_count") + 1,
        last_clicked_at=now,
        first_clicked_at=F("first_clicked_at") if link.first_clicked_at else now,
    )


def serialize_link(link, request=None):
    payload = {
        "id": str(link.id),
        "token": link.token,
        "target_url": link.target_url,
        "label": link.label,
        "recipient_email": link.recipient_email,
        "user_id": str(link.user_id) if link.user_id else None,
        "is_active": link.is_active,
        "click_count": link.click_count,
        "first_clicked_at": link.first_clicked_at,
        "last_clicked_at": link.last_clicked_at,
        "created": link.created,
        "redirect_path": f"/api/communications/r/{link.token}/",
    }
    if request is not None:
        payload["redirect_url"] = request.build_absolute_uri(payload["redirect_path"])
    return payload
