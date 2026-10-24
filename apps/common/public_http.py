"""HTTP helpers for cacheable public API responses."""

from rest_framework.response import Response


def with_public_cache_headers(
    response: Response,
    *,
    max_age: int = 300,
    stale_while_revalidate: int = 600,
) -> Response:
    """Allow browsers and CDNs to reuse stable public JSON for a few minutes."""
    response["Cache-Control"] = (
        f"public, max-age={max_age}, stale-while-revalidate={stale_while_revalidate}"
    )
    response["Vary"] = "Accept, Authorization"
    return response
