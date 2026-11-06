# CYC-104: package credit expiry

## Scope and rollout status

Additive implementation for new PACKAGE purchases only. Existing purchases,
including not-yet-activated purchases, remain grandfathered. Existing wallet
balances are not backfilled, removed or assigned expiry dates. Membership and
gift product behavior is not changed. No cron is needed.

The owner chose a separate non-expiring replacement credit, one per refunded
booking, on November 6 (Slack reply 1793963472.087139). The class-time expiry,
replacement and FAQ/migration release scope were approved in the same thread.
Production release still requires a verified private backup, migration rehearsal
and the normal release gates.

## Accounting

- `Wallet.class_credits` stays the persisted aggregate, including expired lots.
- `available_class_credits` excludes expired remaining quantities lazily.
- Each new package snapshots its plan's `duration_days` when sold. Activation
  creates one lot ending at the end of activation date + those calendar days,
  in the configured studio timezone. Quantity increases credits, not validity.
- Booking locks wallet/lots and spends earliest eligible expiry first, then
  grandfathered credits. Eligibility uses the scheduled class start, not the
  reservation creation time. Exact expiry boundary is inclusive.
- A charged reservation records its lot. Member cancellation restores only that
  lot and never extends expiry. Old charged reservations restore legacy credit,
  even when a later unlimited plan is active.
- Studio cancellation of an expired lot grants a separate one-credit replacement
  tied to the reservation, once. It never expires; it is recorded separately.
- Activation and cancellation use row locks/state rechecks to prevent duplicate
  grants/refunds. A failed reservation rolls back both wallet and lot debits.

## Migration preparation

1. Back up the target database using its supported operator procedure. Preserve
   the backup and verify restore before any production migration.
2. Pause purchase/booking writes for the rollout. Record wallet total/count,
   purchase count, and migration heads.
3. Apply normal Django migrations. New migrations are wallets0009,
   members0010 and faqs0004. The dependency graph is additive, without balance
   updates or historical lot backfill.
4. Confirm pre-existing purchases have `credit_expiry_enabled=false`, existing
   class-credit balances/counts match, and no old purchase gained a lot.
5. Validate new synthetic purchase/booking/cancellation and API balances before
   resuming writes. Deploy the matching frontend disclosure.
6. Keep the application rollback at this schema version. Do NOT reverse these
   migrations after lots/debits exist; that would destroy provenance. A true
   database rollback requires operator-approved backup restore and reconciliation
   of all writes since the backup.

The local PostgreSQL16 rehearsal started at wallets0008/members0009/faqs0003,
with synthetic wallet balance17 and one unactivated existing purchase. Migrating
all heads retained17, marked that purchase grandfathered, created no lots, and
kept expiry enabled for a newly sold PACKAGE. This is not proof of the target
production data or its backup.

## Verification

PostgreSQL tests include simultaneous activation, two debits competing for one
credit, simultaneous cancellation, expired reads, immutable duration, legacy
refund, class-time boundary and atomic rollback. Wallet API query count stays
constant as purchase history grows. Frontend re-reads the catalogue without SWR
before checkout and blocks changed validity pending fresh consent. Local browser
screens use synthetic API fixtures only. No payment gateway is changed.

### Final-policy verification, November 6

On backend `656a4f1`, fresh PostgreSQL runs passed 74 wallet, 124 member,
63 FAQ/plan and 81 analytics/communications tests (342 total). The final
nonexpiring-replacement policy was also rehearsed from the old schema in a
new disposable PostgreSQL database: balance 17 retained, the old unactivated
purchase grandfathered, zero historical lots, new purchase expiry enabled,
and the new FAQ preserved the one-per-refunded-booking nonexpiring exception.
Frontend `487b358` passed its five targeted tests and production build. Cart
and wallet desktop/mobile pixels were inspected with mocked APIs, including
Santiago purchase dates under a Tokyo browser timezone and renewed consent
when catalogue validity changes. These are not production-data checks.

Stock reports/schedules tests are not all green: model_bakery creates random
unspecified Room capacities near the integer limit, and their daily sum can
overflow a report integer. The existing exception logger then raises a
LogRecord `args` collision. Untouched develop `eb66dfd` reproduces this failure
class. A separate diagnostic pytest plugin limiting only unspecified synthetic
Room capacities to 40 makes all 102 reports/schedules tests pass on both
baseline and feature. That diagnostic pass is not a stock-suite pass, and this
credit-expiry change does not alter reporting or scheduling fixtures to hide it.
