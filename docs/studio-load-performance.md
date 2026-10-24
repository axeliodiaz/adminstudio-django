# PulseFit Studio — carga y cold start (Render)

## Despliegue en Render

- **Imagen / comando**: `Dockerfile` → `scripts/render_start.sh` (Gunicorn en `0.0.0.0:80`, migraciones y seeds en segundo plano).
- **Rama que despliega**: `develop` (`origin/HEAD`). Confirmar en el dashboard del servicio *adminstudio-django* (Settings → Build & Deploy → Branch).
- **Mejoras de rendimiento**: merge del PR #187 a `develop` (caché pública, N+1, `/api/healthcheck/live/`).

## Cold start (plan gratuito)

Render apaga el servicio tras ~15 min sin tráfico. La primera petición paga:

1. Arranque del contenedor + Gunicorn.
2. Migraciones/seeds en background (`render_start.sh`).
3. Conexión a Postgres remoto (healthcheck completo y primeros endpoints).

## Keep-alive (GitHub Actions)

Workflow [`.github/workflows/render-keepalive.yml`](../.github/workflows/render-keepalive.yml):

- **Ventana**: solo **08:00–23:59** hora **America/Santiago** (incluye cambio horario de verano vía `TZ=America/Santiago`).
- **Fuera de ventana**: el job termina sin `curl` — el servicio **puede dormir** (no se fuerza uptime nocturno).
- **Intervalo**: cada **10 minutos** (por debajo del spin-down de ~15 min).
- **URL**: `GET /api/healthcheck/live/` (sin base de datos).

### Horas de instancia estimadas (este servicio web)

Render factura **horas de instancia encendida** en el plan free (750 h/mes **por workspace**, compartidas entre todos los servicios free).

Si el keep-alive mantiene el web despierto solo en la ventana diaria:

| Concepto | Cálculo |
|----------|---------|
| Horas despierto / día | 16 h (08:00 → 23:59) |
| Días / mes (media) | ~30,4 |
| **Horas / mes (solo este servicio)** | **16 × 30,4 ≈ 487 h** |

Otros servicios free del mismo workspace (otro web, worker, DB free de Render, etc.) **suman** al mismo cupo de 750 h. Si se supera, Render suspende todos los servicios free hasta el mes siguiente.

**Otras opciones (no implementadas / de pago)**:

| Opción | Coste | Notas |
|--------|-------|--------|
| Plan sin sleep en Render | De pago | Elimina el spin-down. |
| Cron Job de Render | Gratis con límites | Misma lógica de ventana horaria. |
| UptimeRobot / similar | Gratis | Ping externo con horario. |

## Infra desde el repo (sin dashboard Render)

- **No hay `render.yaml`** en el repositorio: la definición del servicio vive en el dashboard de Render (o blueprint no versionado aquí).
- **Un servicio web** documentado por URL: `adminstudio-django.onrender.com` (`Dockerfile` + `scripts/render_start.sh`).
- **Postgres**: producción exige `DATABASE_URL` (ver `adminstudio_django/settings/database.py` y `prod.py`). Los comentarios del código indican **Supabase session pooler** (`*.pooler.supabase.com:5432`), no Postgres free de Render (que expira a 30 días). El host real solo está en el secreto `DATABASE_URL` en Render — **no accesible desde este repo**.
- **Cuántos servicios free hay en el workspace**: requiere dashboard o API de Render; el MCP de Render no está disponible en este entorno.

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

1. **Precalentar API** al montar la app: `fetch(`${API}/healthcheck/live/`)` en paralelo al bootstrap.
2. **React Query / SWR** con `staleTime: 5 * 60_000` para `studios/branding/`, `plans/plans/`, `faqs/`.
3. **Skeleton** en `#pricing` y FAQ en lugar de spinner de pantalla completa.
4. **Respetar `Cache-Control`** del backend en GET públicos.
