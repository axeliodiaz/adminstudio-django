"""Server-side caching for the staff admin wallets and purchases lists (CYC-116).

Tab switches, searches and pagination on Billeteras y compras recompute the
same querysets on every request. The data rarely changes within minutes, so
each payload is cached for five minutes keyed by its filters. The Recargar
button bumps the cache version, forcing the next read to re-query the
database and rebuild the cache - same pattern as the dashboard (CYC-110).
"""

from django.core.cache import cache

_VERSION_KEY = "admin-wallets:version"
_ENTRY_TIMEOUT = 5 * 60  # five minutes, in seconds


def _version() -> int:
    return cache.get_or_set(_VERSION_KEY, 1, timeout=None)


def _key(module: str, params: dict) -> str:
    normalized = "&".join(f"{name}={(value or '')}" for name, value in sorted(params.items()))
    return f"admin-wallets:v{_version()}:{module}:{normalized}"


def get_or_compute(module: str, params: dict, compute):
    """Return the cached payload for the filters, computing and storing it on a miss."""
    key = _key(module, params)
    payload = cache.get(key)
    if payload is not None:
        return payload
    payload = compute()
    cache.set(key, payload, timeout=_ENTRY_TIMEOUT)
    return payload


def invalidate() -> None:
    """Force every cached wallet/purchase payload to recompute on its next read."""
    if not cache.add(_VERSION_KEY, 1, timeout=None):
        cache.incr(_VERSION_KEY)
