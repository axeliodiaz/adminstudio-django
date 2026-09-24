"""Opt-in page-number pagination for list endpoints (CYC-80).

A list endpoint keeps returning a plain JSON array unless the client sends
``page`` or ``page_size``. Then it returns an envelope::

    {"count": 123, "page": 2, "page_size": 50, "total_pages": 3,
     "next_page": 3, "previous_page": 1, "results": [...]}

See docs/api-pagination.md.
"""

from collections.abc import Callable, Iterable
from math import ceil

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class PaginationError(ValueError):
    pass


def wants_pagination(query_params) -> bool:
    return "page" in query_params or "page_size" in query_params


def _positive_int(raw, name: str, default: int) -> int:
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise PaginationError(f"{name} must be a positive integer.") from exc
    if value < 1:
        raise PaginationError(f"{name} must be a positive integer.")
    return value


def paginate(query_params, queryset, serialize: Callable[[object], dict]) -> dict:
    """Slice ``queryset`` for the requested page and serialize only that page."""
    page_size = min(
        _positive_int(query_params.get("page_size"), "page_size", DEFAULT_PAGE_SIZE),
        MAX_PAGE_SIZE,
    )
    page = _positive_int(query_params.get("page"), "page", 1)
    count = queryset.count()
    total_pages = max(1, ceil(count / page_size))
    offset = (page - 1) * page_size
    items: Iterable = queryset[offset : offset + page_size] if offset < count else []
    return {
        "count": count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "next_page": page + 1 if page < total_pages else None,
        "previous_page": page - 1 if page > 1 else None,
        "results": [serialize(item) for item in items],
    }
