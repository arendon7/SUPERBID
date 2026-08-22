# v0.35 — Probe seguro de términos Fasecolda

## Objetivo

Permitir probar un término alternativo contra la búsqueda pública de Fasecolda sin modificar homologaciones, candidatos, readiness ni decisiones económicas.

Esto resuelve una limitación detectada en v0.34: una sugerencia de término más completo puede ser mejor que el término original, pero no siempre produce resultados en la API pública.

## RPC

`dashboard_probe_fasecolda_search_term(external_lot_id, term)`

Valida:
- lote existente;
- ID externo con formato esperado;
- término entre 2 y 80 caracteres;
- preservación de la marca pública del vehículo;
- respuesta HTTP 200 o 404 de la API pública de búsqueda;
- máximo 22 códigos devueltos.

Retorna:
- término probado;
- término actualmente usado por el matcher;
- término sugerido por v0.34;
- HTTP status;
- cantidad de códigos;
- `has_codes`;
- lista de códigos públicos.

## Guardrail

`FASECOLDA_SEARCH_PROBE_NOT_MATCH`

Un probe:
- no es una homologación;
- no es una referencia Fasecolda confirmada;
- no crea candidatos;
- no modifica `lot_fasecolda_matches`;
- no modifica `lot_fasecolda_candidates`;
- no modifica readiness, puja máxima, ROI o `final_decision`.

## Hallazgo inicial

Pruebas productivas de solo lectura confirmaron:
- `TOYOTA COROLLA CROSS` devuelve códigos públicos donde `TOYOTA COROLLA` había quedado `UNMATCHED` para el lote analizado;
- `KIA SPORTAGE` devuelve códigos públicos, por lo que su bloqueo no es ausencia de resultados de búsqueda sino falta de valor compatible para el año del lote;
- algunas expansiones como `NISSAN V DRIVE` o `CITROEN C4 CACTUS` pueden no producir códigos, demostrando por qué la sugerencia no debe aplicarse automáticamente.

## Seguridad

La RPC está revocada a `public`, `anon` y `authenticated`; solo `service_role` puede ejecutarla.

## Siguiente fase

v0.36 podrá usar este probe como precondición de un override manual y auditable del término de búsqueda, sin saltarse el matcher ni el identity guard.
