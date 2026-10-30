# In-app help coverage audit (CYC-423)

Source snapshot: `adminstudio-django` develop `45941db` and
`adminstudio-front` develop `8575d89`, 2026-10-30. This is a source audit,
not a claim that a production database contains all seeded articles.

## Coverage map

The app has two help surfaces: FAQ (Markdown, `apps/faqs`) and Documentation
(HTML articles, `apps/docs`). Reuse their existing access checks rather than
copying all articles into a second public catalog. Documentation migrations
0002-0015 provide the following how-to groups; FAQ seeds cover newer modules.

| Delivered area | Existing source coverage | Audience |
| --- | --- | --- |
| Classes, reservation and spot selection | docs 0002-0003 | Public/member |
| Instructor catalog and schedule, public FAQ, legal pages | docs 0004 | Public/member |
| Plans, cart/checkout, wallet, profile/authentication | docs 0004 | Public/member |
| Reservations, waitlist, cancellations, member stats | docs 0004 | Public/member |
| Dashboard, schedules, reservations, attendance, member administration | docs 0005 | Staff |
| Wallet/purchases, plans/benefits, promo codes | docs 0005 | Staff |
| Staff profile, instructors, users, studios/rooms, settings | docs 0006 | Staff |
| FAQ administration | docs 0006 | Staff; editing still subject to superuser endpoint checks |
| Coach today/schedule/iCal/roster/check-in | docs 0006 | Coach |
| Coach class start, rider notes/setup, playlists, stats/profile | docs 0007 | Coach |
| Transactional email and notification queue explanation | docs 0007 | Platform; existing public article, not changed by this work |
| Gift cards, referrals, first-timer flows, favorite alerts | docs 0009-0011 | Existing section audiences |
| Guest passes and member self check-in | docs 0012-0013 | Existing section audiences |
| Legal/help content editing in Django Admin | docs 0015 | Staff |
| Communications audience/composition/links and unavailable sending | `seed_communications_faq` | Superuser only |
| Branding logo/colors/fonts/reset | `seed_branding_faq` | Superuser only |
| Reports/filtering/freshness/limits | `seed_reports_faq` | Superuser only |
| People directory, roles/search/page controls and limits | **Missing; added `seed_people_inventory_faq`** | Superuser only |
| Base inventory categories/locations/items and limits | **Missing; added `seed_people_inventory_faq`** | Superuser only |

The People/Inventory guides close the delivered base-documentation slice of
CYC-421/422 without claiming future modules shipped. Their broader feature
tickets and current status are not changed here.

## New guides and safeguards

Six additive FAQ entries, in `personas-staff` and `inventario-staff`:
- People directory lookup, role/search/pagination, read-only scope and routes
  to existing user/member/instructor editors.
- Inventory category/location creation, item registration/reference fields,
  and an explicit boundary around stock, laundry, suppliers and audit history.

The existing FAQ endpoint exposes `requires_staff` sections **only to
superusers**, despite that field's legacy name. Anonymous users, members,
coaches and plain staff must not receive these guides. Tests exercise all
five identities. No broadening of Documentation's staff audience is made.

The seed is idempotent and additive. It does not overwrite edited answers,
publication choices, or revive soft-deleted entries. It repairs an accidentally
public target section back to protected. It runs in the existing deploy startup
seed sequence; it does not execute against production as part of this audit.

## Remaining boundaries

- CYC-417 adds supplier contact/product-reference guides; CYC-419 adds the API
  audit guide. CYC-415 extends it with stock/minimum/consumption/laundry/loss
  instructions. These supersede the original base-only inventory boundary.
- Stock starts unknown until an explicit opening count (available and laundry).
  No historical balance or movement backfill is performed. The existing audit
  feed is the movement log, with actor/time/before/after/action/quantity/reason.
- Source coverage does not verify production migration or seed execution.
- People contracts/pay configuration/payroll are not active in the module shell.
- Communications campaign sending/provider selection is not active; keep its
  existing unavailable-feature explanation rather than inventing a Send flow.
- People pagination is delivered on frontend develop via CYC-424, not released
  to main in this pass. The guide qualifies controls as available when present.
- Existing docs/FAQ publication state and editorial changes in the production
  database are unverified. No public disclosure, production seed run, or release
  was performed by the source audit.

## Acceptance for subsequent features

For each delivered workflow, update this map or the owning guide with its entry
point, real steps, result, permission gate and known limits. Test unauthorized
help access and verify actual rendered content. Do not mark a future feature
covered merely because its parent module has a guide.
