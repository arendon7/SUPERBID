# v0.38 — Fasecolda Valuation Workbench

## Objetivo

Unificar los bloqueos `REVIEW_VALUATION` en una cola de trabajo que indique qué workflow humano existente corresponde a cada lote.

Guardrail:

`FASECOLDA_VALUATION_TRIAGE_NOT_MATCH`

El workbench no homologa, no ejecuta probes, no cambia términos, no confirma candidatos y no modifica resultados económicos.

## Fuente central

`dashboard_fasecolda_valuation_workbench` combina únicamente información ya existente de:

- `dashboard_lot_current`;
- `dashboard_economic_readiness_current`;
- `lot_fasecolda_effective_current`;
- `dashboard_fasecolda_resolution_queue`;
- `dashboard_fasecolda_unmatched_diagnostics`.

Solo incluye lotes cuyo `next_action = REVIEW_VALUATION`.

## Workflows

### `CANDIDATE_RESOLUTION`

Para estados efectivos `AMBIGUOUS` o `MEDIUM`.

Se enruta al resolver humano v0.33:
`superbid-fasecolda-dashboard`.

Los casos con 1–3 candidatos reciben `triage_rank=10`; los demás, `20`. Esto prioriza esfuerzo de revisión, no calidad económica ni probabilidad de compra.

### `SEARCH_TERM_WORKFLOW`

Para diagnósticos:
- `SEARCH_TERM_CAN_BE_EXPANDED`;
- `NO_MATCH_ROW`;
- `PUBLIC_SEARCH_RETURNED_NO_CODES`;
- `UNMATCHED_OTHER`.

Se enruta al workflow v0.37:
`superbid-fasecolda-search-dashboard`.

### `YEAR_REFERENCE_REVIEW`

Para `NO_YEAR_COMPATIBLE_REFERENCE`.

Se mantiene separado porque un mejor término de búsqueda no garantiza que exista una referencia Fasecolda utilizable para el año del vehículo.

### `VALUATION_REVIEW_OTHER`

Fallback explícito para cualquier bloqueo de valoración no cubierto por los workflows anteriores.

## Ranking operativo

El ranking solo ordena trabajo:

- 10: 1–3 candidatos públicos;
- 20: AMBIGUOUS/MEDIUM con más candidatos;
- 30: término expandible;
- 40: sin fila de match;
- 45: búsqueda pública sin códigos;
- 50: sin referencia compatible por año;
- 60: otros.

No altera `review_score`, Fasecolda status, puja máxima, ROI ni `final_decision`.

## Dashboard privado

Nueva Edge Function:
`superbid-fasecolda-workbench`

Características:
- autenticación mediante `dashboard_token_valid`;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- server-rendered;
- sin JavaScript cliente;
- filtros por workflow y estado de revisión;
- enlaces a los workflows humanos existentes y al detalle del lote;
- ninguna RPC de escritura de negocio.

## Estado productivo al crear v0.38

La cola contiene 212 bloqueos activos de valoración:

- 62 `CANDIDATE_RESOLUTION` con 1–3 candidatos;
- 76 `CANDIDATE_RESOLUTION` con más candidatos;
- 29 `SEARCH_TERM_WORKFLOW` por término expandible;
- 16 `SEARCH_TERM_WORKFLOW` por `NO_MATCH_ROW`;
- 29 `YEAR_REFERENCE_REVIEW`.

Estos conteos son una fotografía operativa y pueden cambiar con nuevos lotes o revisiones humanas.
