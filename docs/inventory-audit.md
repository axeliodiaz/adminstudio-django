# Inventory API change audit (CYC-419)

The superuser-only GET `/api/inventory/audit/` feed uses standard page/page_size
pagination, newest first, and has no write/delete endpoints. The Inventory UI
shows actor, time, entity/action and expandable before/after snapshots.

Scope: successful category/location/item creation and supplier creation/editing
through the supported inventory API. Snapshot actor ID/name comes from the
authenticated user, never payload. Events and domain writes share a transaction;
an audit insert failure rolls back the domain write. Failed validation and no-op
supplier edits do not generate events. Supplier snapshots include reference
products/prices/lead times, not purchase or stock ledger entries.

The additive migration starts an empty event table. There is no historical
backfill or invented movement record. Direct database edits and Django Admin
writes are not covered; the UI explicitly says so. Future CYC-415 stock/laundry
work must record real domain events through this audit mechanism, not fabricate
history or create a competing ledger. No production migration/run is performed
in this source change.

Permission tests cover anonymous/member/coach/plain staff denial; admin tests
cover snapshots, actor spoofing, all supported writes, read-only endpoint,
validation/no-op exclusions, pagination and transaction rollback.
