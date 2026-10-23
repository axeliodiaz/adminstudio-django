# PulseFit Studio — carga y cold start (Render)

## Despliegue en Render

- **Imagen / comando**: `Dockerfile` → `scripts/render_start.sh` (Gunicorn en `0.0.0.0:80`, migraciones y seeds en segundo plano).
- **Rama que despliega**: el remoto por defecto del repo es `develop` (`origin/HEAD`). Render suele estar enlazado a esa rama; confirmar en el dashboard del servicio *adminstudio-django* (Settings → Build & Deploy → Branch).
- **Este trabajo**: rama `perf/studio-load`, sin merge a `main`/`develop` hasta confirmación explícita.

## Cold start (plan gratuito)

Render apaga el servicio tras ~15 min sin tráfico. La primera petición paga:

1. Arranque del contenedor + Gunicorn.
2. Migraciones/seeds en background (`render_start.sh`).
3. Conexión a Postgres remoto (healthcheck completo y primeros endpoints).

**Mitigación gratuita implementada**: workflow [`.github/workflows/render-keepalive.yml`](../.github/workflows/render-keepalive.yml) hace `GET /api/healthcheck/live/` cada 10 minutos (sin consultar la base).

**Otras opciones (no implementadas / de pago)**:

| Opción | Coste | Notas |
|--------|-------|--------|
| Plan sin sleep en Render | De pago | Elimina el spin-down. |
| Cron Job de Render | Gratis con límites | Misma URL de liveness cada 10–14 min. |
| UptimeRobot / similar | Gratis | Ping externo al mismo endpoint. |

## Endpoints públicos del SPA (bundle `studio.axeldiaz.com`)

Rutas relativas a `https://adminstudio-django.onrender.com/api/`:

| Página / flujo | Endpoints |
|----------------|-----------|
| Planes y promociones (`#pricing`) | `plans/plans/`, `plans/validate-promo/` (POST), `plans/checkout/` |
| Marca / tema | `studios/branding/` |
| Sedes y salas | `studios/studios/`, `studios/rooms/`, `studios/addresses/` |
| FAQ | `faqs/` |
| Legales | `legals/...` (p. ej. términos) |
| Docs de ayuda | `docs/` |

## Caché en el backend

- **Servidor**: `apps/common/public_cache.py` (versión por namespace, TTL 10 min, invalidación en `post_save`/`post_delete`).
- **HTTP**: `Cache-Control: public, max-age=300, stale-while-revalidate=600` en listados públicos estables.
- **Liveness**: `GET /api/healthcheck/live/` — solo JSON `{"status":"ok"}` (sin DB). El healthcheck completo (`/api/healthcheck/`) sigue comprobando Postgres para deploys.

## Frontend (`adminstudio-front`) — sugerencias

Repo no accesible desde este entorno; cambios propuestos en rama `perf/studio-load` del front:

1. **Precalentar API** al montar la app: `fetch(`${API}/healthcheck/live/`)` en paralelo al bootstrap (no bloquear UI).
2. **React Query / SWR** con `staleTime: 5 * 60_000` para `studios/branding/`, `plans/plans/`, `faqs/`.
3. **Skeleton** en `#pricing` y FAQ en lugar de spinner de pantalla completa mientras llegan planes + branding.
4. **Respetar `Cache-Control`** del backend (fetch por defecto en navegador ya cachea GET).

Archivos típicos a tocar: cliente API (`src/api` o similar), layout raíz, página de pricing/promociones.
