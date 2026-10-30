# Inventory stock and laundry (CYC-415)

This extends the existing item catalog and append-only inventory API audit.
Superusers only: anonymous, member, coach and plain staff requests are rejected.

## Workflow

1. Open Inventory > Stock and laundry. Active items without an opening count
   have unknown balances, not zero.
2. Enter the actual available and already-in-laundry counts and minimum. This
   records one opening event, not fabricated historical sends or receipts.
3. Record restock, consumption, laundry send/receive, loss or write-off.
   Loss/write-off requires a reason and an available/laundry source bucket.
4. Change the minimum separately. The restock warning means available < minimum;
   laundry units are not available units. No automatic purchase or alert job runs.
5. Review actor, timestamp, action, quantity, bucket, reason and before/after
   balances in the existing Audit tab. API events are not editable or deletable.

Counts are whole units. Movements cannot overdraw either bucket. Laundry sends
and receipts transfer units without changing the total; consumption, losses and
write-offs reduce it. The current model tracks one balance per item, not batches
or per-location allocations. Item location remains catalog metadata.

## API and safety

- GET `/api/inventory/stock/` paginates active catalog items with nullable counts,
  initialization flag, version and restock warning. Optional name search.
- POST `/api/inventory/stock/<item-uuid>/movements/` accepts an action and integer
  quantity (zero only for opening), or a separate minimum change. Opening may
  include the initial laundry count and minimum; these default to zero.
- Every non-opening write requires the version read from the list. A conditional
  version update prevents stale writes; a replay returns 409. The UI preserves
  the failed form and offers reload, never silently retries a mutation.
- Opening is unique per item. Concurrent duplicate initialization returns 409.
- Stock and audit are in one transaction. Invalid input/no-op minimum changes
  produce no stock or audit event. The authenticated actor cannot be supplied
  by the client. Inactive items cannot move.
- Each request quantity/minimum is bounded at 1,000,000. Balances are also bounded
  by the database positive-integer maximum. Errors never silently clamp values.

Migration 0004 is additive and creates no balances or historical events. No
production backfill, direct database/Admin audit coverage, purchase, payment,
cron or vendor communication is part of this change. Production migration and
FAQ seed execution must be verified during a separately authorized release.

Protected FAQ instructions use exact prior seed matching, preserving edited
answers, unpublished state and soft-deleted items. The coverage audit is updated
for the delivered supplier, audit and stock workflows.
