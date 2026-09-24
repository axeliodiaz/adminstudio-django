# API pagination (CYC-80)

List endpoints use page-number pagination. Rolled out in phases so existing clients didn't break; **phase 3 (current) makes pagination always on** and removes the legacy plain-array mode.

## Contract

Pagination is **always on**. Without `page` or `page_size`, the endpoint returns page 1 with the default page size. The response is always an envelope:

```json
{
  "count": 123,
  "page": 2,
  "page_size": 50,
  "total_pages": 3,
  "next_page": 3,
  "previous_page": 1,
  "results": [ ... same row shape as the plain list ... ]
}
```

| Param       | Default | Rules                                                     |
|-------------|---------|-----------------------------------------------------------|
| `page`      | 1       | Positive integer. A page past the end returns `results: []`. |
| `page_size` | 50      | Positive integer, capped at 200.                          |

- Invalid values (`0`, negative, non-numeric) return `400 {"detail": "..."}`.
- Filters (`search`, `status`, dates, ...) are applied before paging, so `count` is the filtered total.
- Ordering is stable (each endpoint orders by explicit fields), so pages don't overlap.
- Implementation: `apps/common/pagination.py` (`wants_pagination`, `paginate`). A view builds a queryset through its service (`*_queryset`), and `paginate` serializes only the requested slice.

## Endpoint status

| Endpoint                               | Phase | Paginated                                    |
|----------------------------------------|-------|----------------------------------------------|
| `GET /api/members/admin/`              | 1     | yes (opt-in)                                 |
| `GET /api/members/admin/reservations/` | 1     | yes (opt-in)                                 |
| `GET /api/auth/users/` (admin users)   | 2     | yes (opt-in)                                 |
| `GET /api/schedules/admin/schedules/`  | 2     | yes (opt-in)                                 |
| `GET /api/schedules/`                  | 2     | yes (opt-in)                                 |
| Public instructors / studios / plans / FAQs | 3 | not planned (small lists)                    |

## Phases

1. **Backend opt-in** (this change): admin members and admin reservations accept `page`/`page_size`.
2. **Front adoption + remaining backends** (this change): admin users, admin schedules and public schedules accept `page`/`page_size`; admin tables request pages and show pager controls; the reservation-form member picker switches to `?search=...&page_size=20`.
3. **Default on** (this change): the five endpoints below paginate by default (`page=1`, `page_size=50`) and the plain-array mode is removed. Front callers were made pagination-safe first (adminstudio-front #87/#88: full-list callers pin `page_size=200`; tables and pickers were already paged).
