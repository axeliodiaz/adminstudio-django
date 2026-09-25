"""Server-side caching for the staff admin dashboard.

The dashboard client fires one request per rendered module (18+) on every
page load, and each request recomputes the same aggregates. On the free
Render tier those queries take seconds, leaving cards on skeleton loaders.
This caches each module payload in the shared (database) cache until it
expires or a staff user taps the reload button, which bumps the cache
version and forces every module to recompute against the database on its
next read.
"""

from django.core.cache import cache
from django.utils import timezone

_VERSION_KEY = "admin-dashboard:version"
_ENTRY_TIMEOUT = 24 * 60 * 60  # one day, in seconds


def _version() -> int:
    return cache.get_or_set(_VERSION_KEY, 1, timeout=None)


def _key(module: str, days: int) -> str:
    today = timezone.localdate().isoformat()
    return f"admin-dashboard:v{_version()}:{module}:{days}:{today}"


def get_or_compute(module: str, days: int, compute):
    """Return the cached payload for a module, computing and storing it on a miss.

    The cache key embeds the cache version, the days period and the local
    date, so a reload-button invalidation and a new day both recompute.
    """
    key = _key(module, days)
    payload = cache.get(key)
    if payload is not None:
        return payload
    payload = compute()
    cache.set(key, payload, timeout=_ENTRY_TIMEOUT)
    return payload


def invalidate() -> None:
    """Force every cached dashboard payload to recompute on its next read."""
    if not cache.add(_VERSION_KEY, 1, timeout=None):
        cache.incr(_VERSION_KEY)
