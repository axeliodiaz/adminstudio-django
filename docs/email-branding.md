# Transactional email branding

All HTML renderers accept an optional `branding` mapping and remain pure. The
callers resolve `email_branding(studio)` for class events and `email_branding()`
for account-wide messages. Identity, purchases, gifts and memberships have no
studio ownership today; default branding is intentional, never inferred from a
member's booking history. This does not change sender addresses, providers,
recipients, send triggers, payment gateways or schedules.

The selected colors, name, tagline and fonts are escaped/validated into inline
styles. The logo is a PNG from the frontend `/api/brand-logo?studio=<uuid>`
endpoint, which rasterizes the backend-sanitized SVG. Ship the matching frontend
PR before enabling these emails in production. External images can be blocked
by an email client; the name remains visible. Web fonts have Arial/Georgia
fallbacks. Class action links preserve the known studio query parameter.

No schema migration or live email sends are required by this change. Tests mock
all send providers. Visual previews use synthetic branding and rider data.
