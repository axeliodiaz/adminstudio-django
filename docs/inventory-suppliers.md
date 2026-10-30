# Inventory suppliers (CYC-417)

Admin-only reference directory. `GET/POST /api/inventory/suppliers/` and
`PATCH /api/inventory/suppliers/<uuid>/` share the existing superuser inventory
gate. List supports search (name/contact), page and page_size, with the standard
pagination envelope. No purchasing, vendor messaging or payment action exists.

A supplier stores name, contact name, email, phone, notes and product references.
Each product has name, optional decimal price, an explicit supported currency
(CLP/USD/EUR), optional lead time in days, and notes. Null means unknown, distinct
from a known zero. Prices are reference quotes, not stock values or obligations.
No existing category/item/location data is changed by the additive migration.

PATCH without products preserves them. Supplying products replaces the reference
list atomically after complete validation; [] clears it. Failed input leaves all
previous rows intact. This is not a stock movement or historical purchase ledger.
Supplier deletion is not exposed by the UI/API. Existing soft-deleted suppliers
are excluded and cannot be revived through PATCH.

Frontend: Inventory > Proveedores, add/edit contact and product rows, search and
paginated list. Auth handling follows existing inventory requests. Unknown prices
and lead times are labeled explicitly. Scope excludes purchases, payment gateways,
stock/laundry, supplier emails, production seed runs and production release.

Help: the admin-only FAQ seed adds a supplier how-to and stops describing supplier
references as unimplemented. Existing edited answers remain preserved by its
additive seed policy; production editorial state is not overwritten or verified.
