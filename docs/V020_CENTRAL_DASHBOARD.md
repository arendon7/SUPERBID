# v0.20 — Dashboard central sobre Supabase

## Objetivo
Eliminar la dependencia del dashboard respecto a SQLite local. La operación 24/7 ya vive en Supabase y la interfaz debe leer esa misma fuente central.

## Arquitectura

`Superbid -> Supabase collector -> Fasecolda -> review queue -> market validation -> dashboard_lot_current -> Edge API/dashboard`

## Vista central
`dashboard_lot_current` combina:
- puja actual y número de pujas;
- cierre;
- comisión pública;
- Fasecolda actual e histórico;
- peritajes;
- review score/state;
- estado de comparables de mercado;
- costos revisados;
- puja máxima y ROI solo cuando estén validados.

## API privada
Edge Function `superbid-read-api`:
- `/health`
- `/summary`
- `/review-queue`
- `/lots/{external_lot_id}`
- `/history`

Requiere Bearer token o `X-Superbid-Read-Key`. El token se valida en servidor contra un secreto en Supabase Vault. El navegador nunca conoce `service_role`.

## Dashboard privado
Edge Function `superbid-dashboard`:
- server-rendered;
- sin JavaScript cliente;
- login por POST;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- filtros REVIEW_NOW/REVIEW_SOON/WATCH;
- detalle por lote;
- enlaces a peritajes públicos;
- muestra explícitamente que REVIEW_NOW no significa COMPRAR.

URL productiva:
`https://bxsfxydhuaqlkfoicbaz.supabase.co/functions/v1/superbid-dashboard`

## Secretos
El valor de `superbid_dashboard_read_token` se provisiona en Supabase Vault y nunca se guarda en GitHub, migraciones, tablas analíticas o JavaScript cliente.

## Seguridad
- `dashboard_lot_current`: solo `service_role`.
- `dashboard_token_valid`: solo `service_role`.
- `dashboard_summary`: solo `service_role`.
- Edge Functions usan custom auth; por eso `verify_jwt=false` es deliberado.
- respuestas con `cache-control: no-store`.
