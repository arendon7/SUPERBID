# v0.11 — Discovery paginado y Fasecolda central

## Discovery
Una fuente `paginated` conserva los parámetros públicos ya verificados de Superbid
y modifica únicamente `pageNumber` y `pageSize`. El collector se detiene en la primera
página vacía posterior al inicio, deduplica por `external_lot_id` y encola cada lote.

Variables:
- `SUPERBID_DISCOVERY_PAGINATED_URLS`
- `SUPERBID_DISCOVERY_MAX_PAGES` (default 10)
- `SUPERBID_DISCOVERY_PAGE_SIZE` (default 30)

No se incorpora un slug colombiano hasta observarlo directamente en producción.

## Contrato JSON
v2 soporta `winner_bid` como número, cadena u objeto monetario; agrega
`total_bidders` y `commission_percent_public` a evidencia. Nunca persiste
`reserved_price` ni identidad de pujadores.

## Fasecolda
Cada registro usa `record_key = SHA256(fuente + referencia + servicio + año)`.
Esto permite reimportar y sincronizar una guía sin duplicar registros.
