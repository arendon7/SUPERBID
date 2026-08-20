# v0.15 — Supabase database-native worker

## Objetivo

Operar discovery y refresh de subastas vehiculares 24/7 sin depender de un computador, Render o un navegador persistente.

## Extensiones

- `http`: lectura HTTP pública de Superbid.
- `pg_cron`: programación de discovery/refresh.

## Endpoints públicos usados

- `https://offer-query.superbid.net/offers/`
- `https://offer-query.superbid.net/seo/offers/`

No se utilizan autenticación, cookies, CAPTCHA bypass, `filter` opaco ni `fieldList`.

## Discovery

`public.superbid_discover_open_vehicles(10,100)` pagina inventario `searchType=opened` y filtra:

- Autos `10000`;
- Camiones `10022`;
- `offerTypeId=1`;
- `isShopping=false`;
- `shoppingOfferType=false`.

Cada lote se upserta y se añade idempotentemente a `collection_queue`.

## Refresh

`public.superbid_refresh_due(40)` procesa la cola en orden de prioridad. Para cada lote consulta `/seo/offers/`, almacena snapshot y recalcula `next_run_at`.

### Cadencia

| Ventana | Próximo refresh |
|---|---:|
| >24 h | 4 h |
| 24–2 h | 30 min |
| 2 h–15 min | 5 min |
| <15 min | 1 min |
| 0–2 h después | 5 min |
| 2–24 h después | 30 min |
| 1–14 días después | 6 h |
| 14–30 días después | 24 h |

Después de 30 días sin estado terminal explícito, el lote puede pasar a `PAUSED`; no se inventa `NOT_SOLD`.

## Resultados

- `SOLD_CONFIRMED` solo si `offerStatus.sold=true`.
- `WITHDRAWN` si `offerStatus.removed=true`.
- `AFTER_MARKET` para propuesta/precio posterior.
- `CLOSED_OBSERVED` para cierre sin confirmación de venta.
- `ACTIVE` para puja abierta.

El precio de cierre observado y el precio de venta confirmado permanecen en campos separados.

## Fecha de cierre

`endDateTime` en epoch milisegundos es la referencia canónica. Evita ambigüedad de zona horaria del campo textual `endDate`.

## Peritajes

`product.attachments` se procesa directamente:

- `PERITAJE`, `INSPECCION`, `AVALUO` -> `PERITAJE`;
- PDF restantes -> `DOCUMENTO`;
- otros -> `ANEXO`.

Se guarda URL pública, nombre y tipo. `galleryJson` se excluye.

## Seguridad

Las funciones `SECURITY DEFINER` operativas tienen ejecución revocada para `PUBLIC`, `anon` y `authenticated`. `service_role` conserva ejecución para administración. Los cron jobs se ejecutan internamente en PostgreSQL.

No se persisten:

- `reservedPrice`;
- identidad de pujadores/compradores;
- teléfonos/datos del seller distintos del nombre empresarial;
- cookies/sesiones/tokens;
- respuesta JSON cruda.

## Cron

- `superbid-discovery-v15`: `*/15 * * * *`
- `superbid-refresh-v15`: `* * * * *`

Los jobs son idempotentes y sus resultados se auditan en `collection_runs` y `cron.job_run_details`.
