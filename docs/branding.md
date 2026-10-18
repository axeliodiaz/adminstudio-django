# Studio branding (CYC-427)

Singleton `StudioBranding` (pk 1) in the database. No file storage: the logo is sanitized SVG text.

| Endpoint | Access | Purpose |
|---|---|---|
| `GET /api/studios/branding/` | public | Theme tokens so the UI can style itself before login |
| `GET/PATCH /api/studios/admin/branding/` | superuser | Read (with `options.fonts` and `options.defaults`) and partial update |
| `POST /api/studios/admin/branding/reset/` | superuser | Restore defaults |

Fields: `name`, `tagline`, `logo_svg`, `primary_color`, `secondary_color`, `background_color`, `text_color` (`#RRGGBB`), `heading_font`, `body_font` (allowlist in `apps/studios/branding.py`).

Default base color is indigo `#4F46E5` (not the old gold `#C9A66B`).

## SVG sanitizer

Allowlist of elements and attributes. Upload is rejected when it has `script`, `foreignObject`, `style`, `image`, `a`, animation elements, a DOCTYPE/entities, no `viewBox`, or more than 100 KB. Event handlers, non-`#` references and unsafe `style`/`url()` values are stripped. An empty `logo_svg` removes the logo.
