# v0.34 — Diagnóstico de Fasecolda UNMATCHED

## Objetivo

Separar los lotes bloqueados en `REVIEW_VALUATION` por causa técnica antes de permitir cualquier corrección manual del término de búsqueda.

v0.34 es deliberadamente **read-only**. No reintenta búsquedas, no crea candidatos, no modifica matches y no cambia el readiness económico.

## Nueva función

`fasecolda_suggest_search_term(title)` propone un término más completo a partir del título público del lote.

La sugerencia:
- elimina marcadores de generación entre corchetes;
- conserva marca + hasta dos tokens de línea;
- permite tres tokens de línea cuando aparece `NEW`;
- se detiene ante marcadores de especificación como `CC`, `MT`, `AT`, `TP`, `TD`, `4X2`, `4X4`;
- se detiene ante números de tres o cuatro dígitos que suelen corresponder a cilindraje.

Ejemplos de problemas que ahora pueden identificarse como término expandible:
- `TOYOTA 4` → `TOYOTA 4 RUNNER`;
- `VOLKSWAGEN T` → `VOLKSWAGEN T CROSS`;
- `NISSAN V` → `NISSAN V DRIVE`;
- `TOYOTA COROLLA` → `TOYOTA COROLLA CROSS`;
- `CITROEN C4` → `CITROEN C4 CACTUS`;
- `NISSAN NEW X` → `NISSAN NEW X TRAIL`.

La sugerencia no se utiliza automáticamente para homologar.

## Vista diagnóstica

`dashboard_fasecolda_unmatched_diagnostics`

Solo incluye lotes cuyo `next_action` es `REVIEW_VALUATION` y cuyo estado Fasecolda efectivo es `UNMATCHED` o no tiene fila de match.

Clasificaciones:
- `SEARCH_TERM_CAN_BE_EXPANDED`: el término sugerido difiere del término utilizado;
- `NO_YEAR_COMPATIBLE_REFERENCE`: la búsqueda produjo referencias pero ninguna con valor utilizable para el año del lote;
- `PUBLIC_SEARCH_RETURNED_NO_CODES`: la búsqueda pública no produjo códigos;
- `NO_MATCH_ROW`: el lote no tiene aún fila en `lot_fasecolda_matches`;
- `UNMATCHED_OTHER`: caso residual que requiere investigación.

## Priorización

`diagnostic_rank` prioriza primero los casos con una expansión concreta del término, luego los que no tienen fila de match y después los faltantes atribuibles a la fuente pública.

## Guardrail

`FASECOLDA_UNMATCHED_DIAGNOSTIC_NOT_MATCH`

Una sugerencia no es una homologación, no es un match, no es evidencia de valor y no altera `final_decision`, puja máxima ni ROI.

## Seguridad

La función y la vista están revocadas a `public`, `anon` y `authenticated`; el acceso operativo queda restringido a `service_role`.

## Estado productivo al crear v0.34

La cola inicial de 74 casos se separó en:
- 29 `SEARCH_TERM_CAN_BE_EXPANDED`;
- 29 `NO_YEAR_COMPATIBLE_REFERENCE`;
- 16 `NO_MATCH_ROW`.

La siguiente fase será un override manual y auditable del término de búsqueda, con confirmación humana y reejecución del matcher normal.
