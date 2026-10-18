# Reports module (precomputed metrics)

Owner request (2026-10-18): reports must read **precomputed data from their
own tables**, not live aggregates, and the platform has **no cron / no 24-7
backend** (free-tier decision). This document describes how the module keeps
that contract.

## Tables (`apps.reports`)

| Table | Grain | Contents |
| --- | --- | --- |
| `DailyMetrics` | one row per (date, studio scope) | classes, reservations, occupancy, waitlist, revenue/purchases, promo, gift cards, guest passes, referrals, notifications, link clicks, ratings, new members, `attendee_ids` (retention) |
| `ClassMetrics` | one row per non-draft class | capacity, booked/attended/missed/cancelled, waitlist, occupancy, rating |

Both carry a **nullable `studio` FK**: today only the global (`NULL`) scope
is written (unique constraints cover both scopes), so per-studio scoping
(CYC-433) is a compute change, not a data migration.

**Bucketing rule:** operational metrics (classes, reservations, waitlist
conversions, ratings) are bucketed by the *class* local date; commercial and
communication metrics (purchases, gift cards, guest passes, referrals,
notifications, clicks, new members) by the *event* local date.

## Freshness model (no cron)

1. **Event-driven.** `post_save` signals (`apps/reports/signals.py`)
   recompute the affected day/class on every relevant write: reservations,
   schedules, waitlist, class ratings, plan purchases, gift cards, guest
   passes, referrals, notifications, tracked-link clicks, members.
2. **Explicit hooks for bulk updates.** `queryset.update()` bypasses
   signals, so the two bulk paths in `apps/members/services.py`
   (`reconcile_no_show_reservations`, `mark_remaining_attendance_missed`)
   call `refresh_schedules()` explicitly.
3. **Deploy-time rebuild.** `render_start.sh` runs
   `python manage.py refresh_reports` on every deploy, healing any drift.
4. **Manual refresh.** `POST /api/reports/refresh/` (superuser) or
   `python manage.py refresh_reports` rebuilds everything on demand.

A failing recompute never breaks the source write: signal handlers log and
swallow exceptions, and the next deploy/refresh heals the row.

Known approximation: a schedule moved to another date refreshes the new
date; the old date is healed on the next deploy/refresh.

## API (superuser only, `IsReportsAdmin`)

- `GET /api/reports/` — catalog, freshness (`first_day`, `last_computed_at`), row counts.
- `GET /api/reports/<key>/?from=YYYY-MM-DD&to=YYYY-MM-DD` — one report
  (`attendance`, `occupancy`, `revenue`, `retention`, `waitlist`,
  `instructors`, `promotions`, `communications`). Range is inclusive,
  defaults to the last 30 days and caps at 400.
- `POST /api/reports/refresh/` — full rebuild.

Every payload is built from `DailyMetrics` / `ClassMetrics` only.

## Not implemented (missing source data)

Fitco-style reports that need data we do not have are tracked as proposed
tickets, not faked: cash close / income-expenses (CYC-446), debts (CYC-447),
staff clock-in/out and pay (CYC-448), prospect conversion (CYC-449),
notification delivery/read (CYC-450), inventory movements (CYC-451).

Days are bucketed in the Django default timezone (UTC), consistent with the
admin dashboard.
