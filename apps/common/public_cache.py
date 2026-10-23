"""Versioned cache for rarely-changing public API payloads (PulseFit Studio).

Uses the shared database cache backend so all gunicorn workers see the same
entries. Model saves bump a namespace version so the next read recomputes.
"""

from collections.abc import Callable
from typing import Any

from django.core.cache import cache

_ENTRY_TIMEOUT = 10 * 60  # ten minutes


def _version_key(namespace: str) -> str:
    return f"public-api:{namespace}:version"


def _version(namespace: str) -> int:
    return cache.get_or_set(_version_key(namespace), 1, timeout=None)


def _entry_key(namespace: str, params: dict[str, str]) -> str:
    normalized = "&".join(f"{name}={value}" for name, value in sorted(params.items()))
    return f"public-api:v{_version(namespace)}:{namespace}:{normalized}"


def get_or_compute(
    namespace: str,
    params: dict[str, str],
    compute: Callable[[], Any],
    *,
    timeout: int = _ENTRY_TIMEOUT,
) -> Any:
    """Return a cached payload for ``namespace`` + ``params``, or compute it."""
    key = _entry_key(namespace, params)
    payload = cache.get(key)
    if payload is not None:
        return payload
    payload = compute()
    cache.set(key, payload, timeout=timeout)
    return payload


def invalidate(namespace: str) -> None:
    """Drop cached payloads for ``namespace`` on the next read."""
    version_key = _version_key(namespace)
    if not cache.add(version_key, 1, timeout=None):
        cache.incr(version_key)
