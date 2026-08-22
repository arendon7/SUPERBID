# v0.39 — Diagnóstico Fasecolda de referencias por año

## Objetivo

Dar un workflow específico a los casos `NO_YEAR_COMPATIBLE_REFERENCE` sin transformar valores de otros años en una valoración del vehículo analizado.

Guardrail obligatorio:

`FASECOLDA_YEAR_REFERENCE_DIAGNOSTIC_NOT_VALUATION`

## Fuente

`dashboard_fasecolda_year_reference_diagnostics` parte exclusivamente de los casos ya diagnosticados como `NO_YEAR_COMPATIBLE_REFERENCE` y consulta las observaciones importadas en `fasecolda_values` para la marca/línea derivada del término de búsqueda.

La vista no modifica el matcher, candidatos, overrides, readiness ni resultados económicos.

## Evidencia expuesta

Para cada lote muestra:
- marca almacenada y marca derivada del término;
- línea buscada;
- años Fasecolda realmente disponibles;
- número de códigos y filas de referencia;
- año inferior más cercano y distancia en años;
- rango mínimo/máximo observado directamente para ese año inferior;
- códigos del año inferior;
- año superior más cercano y distancia;
- rango mínimo/máximo observado directamente para ese año superior;
- códigos del año superior;
- fecha de importación de la evidencia.

Los rangos son observaciones directas de los años indicados. No existe campo de valor estimado/interpolado para el año faltante.

## Razones diagnósticas

- `STORED_BRAND_DIFFERS_FROM_SEARCH_TERM`: la marca estructurada del lote no coincide con la marca contenida en el término de búsqueda. Debe revisarse identidad antes de cualquier conclusión de año.
- `LINE_NOT_PRESENT_IN_IMPORTED_VALUES`: la línea buscada no aparece en el import disponible bajo la marca del término.
- `SAME_YEAR_REFERENCE_EXISTS_DIAGNOSTIC_STALE`: apareció una referencia del mismo año y el diagnóstico previo puede estar desactualizado; exige revisar frescura del matcher.
- `YEAR_GAP_BETWEEN_REFERENCES`: existen años inferiores y superiores, pero no el año exacto.
- `ONLY_OLDER_REFERENCES`: solo existen observaciones de años anteriores.
- `ONLY_NEWER_REFERENCES`: solo existen observaciones de años posteriores.
- `REFERENCE_YEARS_UNAVAILABLE`: fallback explícito.

## Acciones sugeridas

Las acciones son de revisión, no escrituras:
- `REVIEW_BRAND_IDENTITY`;
- `RECHECK_MATCHER_FRESHNESS`;
- `REVIEW_YEAR_GAP_EVIDENCE`;
- `REVIEW_OLDER_REFERENCE_EVIDENCE`;
- `REVIEW_NEWER_REFERENCE_EVIDENCE`;
- `REVIEW_SOURCE_COVERAGE`.

## Dashboard privado

Nueva Edge Function:
`superbid-fasecolda-year-dashboard`

Características:
- autenticación con `dashboard_token_valid`;
- cookie propia `HttpOnly; Secure; SameSite=Strict`;
- server-rendered y sin JavaScript cliente;
- filtros por razón diagnóstica y estado de revisión;
- muestra evidencia inferior/superior y códigos;
- enlaza al detalle del lote, búsqueda Fasecolda y workbench;
- no contiene RPC de escritura de negocio.

El workbench v0.38 se actualiza para que `YEAR_REFERENCE_REVIEW` abra este dashboard especializado.

## Semántica prohibida

v0.39 no:
- interpola entre años;
- extrapola desde un año anterior o posterior;
- aplica inflación/depreciación para fabricar el año faltante;
- copia un valor vecino a `fasecolda_current_cop`;
- fuerza una homologación;
- cambia `review_score`, puja máxima, ROI o `final_decision`.

## Fotografía inicial

Al crear v0.39, los 29 casos se distribuían así:
- 16 `YEAR_GAP_BETWEEN_REFERENCES`;
- 8 `LINE_NOT_PRESENT_IN_IMPORTED_VALUES`;
- 2 `ONLY_OLDER_REFERENCES`;
- 1 `ONLY_NEWER_REFERENCES`;
- 2 `STORED_BRAND_DIFFERS_FROM_SEARCH_TERM`.

Los conteos son operativos y pueden cambiar cuando ingrese nueva evidencia o se corrija identidad/matching.
