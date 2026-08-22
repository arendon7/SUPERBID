# v0.36 — Override manual y auditable del término Fasecolda

## Objetivo

Permitir que un humano confirme un término de búsqueda alternativo para un lote cuando el diagnóstico v0.34 y el probe v0.35 demuestren que el término derivado del título es insuficiente.

El override **no es una homologación** y nunca fuerza un resultado `HIGH`. Después de confirmarse, se vuelve a ejecutar el matcher Fasecolda normal completo con el término aprobado.

## Persistencia

- `lot_fasecolda_search_term_overrides`: override vigente por lote;
- `lot_fasecolda_search_term_override_history`: historial inmutable de `CONFIRM`, `CLEAR` e `INVALIDATE_IDENTITY_CHANGE`.

El historial conserva el término anterior/nuevo y snapshots del match anterior y resultante.

## Matcher

`fasecolda_effective_search_term(lot_id,title)` usa:
1. override confirmado si existe;
2. `fasecolda_search_term(title)` en caso contrario.

La migración preserva la definición existente de `fasecolda_match_lot` y parchea únicamente la línea que obtiene el término de búsqueda. Ranking de candidatos, filtro por año, scoring y umbrales `HIGH/MEDIUM/AMBIGUOUS` permanecen en el matcher original.

## Confirmación

`dashboard_set_fasecolda_search_term_override(..., action='CONFIRM')` exige:
- lote válido;
- término normalizado entre 2 y 80 caracteres;
- preservación de la marca del vehículo;
- ausencia de una resolución manual de candidato v0.33 activa;
- probe v0.35 con al menos un código público;
- confirmación realizada por el backend/UI que invoque la RPC.

Luego guarda el término y ejecuta `fasecolda_match_lot(lot_id,true)`. El resultado puede seguir siendo `UNMATCHED`, `AMBIGUOUS`, `MEDIUM` o `HIGH`.

## Reversión

`CLEAR` elimina el override y vuelve a ejecutar el matcher normal con el término derivado del título.

## Cambio de identidad

Si cambian `title`, `brand`, `line` o `model_year`:
- se registra `INVALIDATE_IDENTITY_CHANGE`;
- se elimina el override;
- se eliminan candidatos y match derivados para evitar una valoración obsoleta;
- la nueva identidad debe volver a pasar por matching.

## Proveniencia

`lot_fasecolda_effective_current.match_origin` distingue:
- `AUTOMATIC`;
- `MANUAL_SEARCH_TERM`;
- `MANUAL_CONFIRMED`.

También expone `search_term_origin`, `search_term_override` y `search_term_overridden_at`.

## Guardrail

`MANUAL_FASECOLDA_SEARCH_TERM_NOT_MATCH`

Un término confirmado no es por sí solo un match ni una valoración confirmada. El matcher sigue determinando el estado y v0.33 sigue siendo el único mecanismo para confirmar humanamente un candidato `AMBIGUOUS/MEDIUM`.

## Seguridad

Tablas y RPC están cerradas a `public`, `anon` y `authenticated`; solo `service_role` puede operar el flujo.

## Certificación

Durante la certificación no se ejecuta ningún override real. La estructura se valida con 0 overrides activos y con pruebas que prohíben cualquier asignación directa a `HIGH` dentro de la RPC.
