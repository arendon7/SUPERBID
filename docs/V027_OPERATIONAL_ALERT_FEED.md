# v0.27 — Feed de alertas operativas

## Objetivo

Convertir cambios operativos relevantes en eventos persistentes y deduplicados sin alterar la valoración económica.

Cada alerta conserva explícitamente:

`OPERATIONAL_ALERT_NOT_BUY_SIGNAL`

Una alerta significa **revisar/atender**, no una recomendación de compra.

## Tipos iniciales

### `CLOSING_2H` — URGENT

Se genera una vez por fecha de cierre cuando un lote está:

- `REVIEW_NOW`;
- abierto;
- a menos de 2 horas del cierre vigente.

Si Superbid extiende el cierre, la nueva fecha produce una clave distinta y puede originar una alerta posterior cuando vuelva a entrar en la ventana de 2 horas.

### `HIGH_PRESSURE` — WARNING

Se genera para `REVIEW_NOW` o `REVIEW_SOON` cuando la presión competitiva es `HIGH` y hubo actividad en las últimas 2 horas.

Para evitar spam, la deduplicación agrupa el episodio por lote y hora del último cambio observado.

### `CLOSE_EXTENSION` — INFO

Se deriva exclusivamente de snapshots consecutivos donde:

`new_closes_at > previous_closes_at`

Cada extensión usa `snapshot_id` en su clave de deduplicación. No se infiere una extensión por ausencia de cierre ni por cambios de precio.

## Persistencia

Tabla:

`operational_alert_events`

Campos principales:

- lote;
- tipo;
- severidad;
- `dedupe_key UNIQUE`;
- momento de disparo;
- momento observado en la fuente;
- puja/cierre/review state/presión/prioridad al dispararse;
- headroom preliminar;
- peritaje;
- mensaje;
- evidencia estructurada derivada;
- interpretación;
- campos de reconocimiento reservados para una versión posterior.

No se guardan identidad de pujadores, `reservedPrice`, cookies ni evidencia cruda de snapshots.

## Ejecución

`refresh_operational_alerts()` corre cada minuto mediante:

`superbid-operational-alerts-v27`

Todos los inserts usan:

`ON CONFLICT(dedupe_key) DO NOTHING`

Por tanto, ejecuciones repetidas son idempotentes respecto de un mismo evento.

## Dashboard

Nueva página privada:

`/functions/v1/superbid-dashboard/alerts`

Filtros:

- tipo;
- severidad.

Ordena por `source_observed_at`, no por la hora de retrocarga, para mantener cronología operacional real.

## API privada

`GET /alerts`

Filtros:

- `type`;
- `severity`;
- `open`;
- `limit`.

La autenticación sigue usando el token privado del read API.

## Seguridad

- tabla con RLS y sin policies públicas;
- tabla, vista y función revocadas a `public`, `anon` y `authenticated`;
- lectura/ejecución para `service_role`;
- dashboard mantiene cookie `HttpOnly; Secure; SameSite=Strict`;
- no existe acción de compra ni modificación de puja máxima desde el feed.
