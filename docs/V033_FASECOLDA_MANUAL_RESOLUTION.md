# v0.33 — Resolución manual y auditable de homologación Fasecolda

## Objetivo

Resolver de forma humana los casos en los que el matcher automático ya produjo candidatos públicos compatibles, pero no tiene evidencia suficiente para declarar un match `HIGH`.

Guardrail obligatorio:

`MANUAL_FASECOLDA_RESOLUTION_NOT_AUTOMATIC_MATCH`

Una resolución manual nunca reescribe el match automático original. El sistema conserva ambos estados y expone el origen efectivo.

## Alcance inicial

La acción `CONFIRM` se permite únicamente cuando:
- existe un match automático;
- su estado es `AMBIGUOUS` o `MEDIUM` (salvo una resolución manual previa que se esté corrigiendo);
- el código seleccionado pertenece a `lot_fasecolda_candidates` del mismo lote;
- el año del candidato coincide con el año del lote;
- existe valor Fasecolda utilizable;
- la referencia existe en `fasecolda_references`;
- el candidato vuelve a pasar `fasecolda_line_compatible`.

`UNMATCHED` permanece bloqueado porque no existe un candidato defendible que confirmar.

## Persistencia

### Estado actual
`lot_fasecolda_manual_resolutions`

Mantiene como máximo una resolución activa por lote.

### Auditoría
`lot_fasecolda_manual_resolution_history`

Acciones:
- `CONFIRM`;
- `CLEAR`;
- `INVALIDATE_IDENTITY_CHANGE`.

El historial conserva referencia anterior, referencia elegida, valor, score/rank del candidato, momento de evaluación y nota humana.

## Reversibilidad

`CLEAR` elimina únicamente la resolución manual actual. El match automático original vuelve a regir inmediatamente y permanece intacto en `lot_fasecolda_matches`.

Si cambian `title`, `brand`, `line` o `model_year` del lote, un trigger invalida automáticamente la homologación manual y registra `INVALIDATE_IDENTITY_CHANGE`.

## Match efectivo

`lot_fasecolda_effective_current` implementa:
- sin resolución manual → campos automáticos originales;
- con resolución manual → `status=HIGH` para habilitar el motor económico, usando el candidato confirmado;
- `match_origin=MANUAL_CONFIRMED`;
- `automatic_status`, `automatic_best_code`, `automatic_best_description` y `automatic_best_score` permanecen disponibles.

La confianza efectiva manual se registra como confirmación humana, pero el origen impide presentarla como resultado automático.

## Propagación

`lot_intelligence_current` usa el match efectivo.

`dashboard_lot_current` añade al final:
- `fasecolda_match_origin`;
- `fasecolda_automatic_status`;
- `fasecolda_automatic_best_code`;
- `fasecolda_manual_resolved_at`;
- `fasecolda_match_interpretation`.

`dashboard_economic_readiness_current` también expone origen y estado automático original.

## Cola de resolución

`dashboard_fasecolda_resolution_queue` contiene:
- identidad del lote;
- match automático y scores;
- estado de resolución manual;
- resolución vigente si existe;
- candidatos públicos como JSON ordenado por `rank_no`.

Por defecto, el flujo humano está pensado para los 145 casos `AMBIGUOUS` y 10 `MEDIUM` observados al crear v0.33.

## Dashboard privado

Función:
`superbid-fasecolda-dashboard`

Características:
- autenticación privada mediante `dashboard_token_valid`;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- filtros por estado automático y resolución manual;
- ningún candidato aparece preseleccionado;
- `CONFIRM` exige elegir un candidato y marcar una confirmación explícita;
- `CLEAR` exige una confirmación independiente;
- notas de hasta 2.000 caracteres;
- server-rendered y sin JavaScript cliente.

El tablero de readiness enlaza `REVIEW_VALUATION` con este resolver y muestra `AUTOMATIC` o `MANUAL_CONFIRMED` junto al estado Fasecolda.

## Seguridad

Tablas, vistas y RPC de resolución están revocadas para `anon` y `authenticated`. Solo el backend `service_role` puede leer/escribir o ejecutar la resolución.

## Límites deliberados

v0.33 no:
- inventa candidatos para `UNMATCHED`;
- selecciona automáticamente el candidato de mayor score;
- convierte un candidato en homologación sin acción humana;
- elimina el match automático original;
- confirma una venta, una puja o una decisión de compra;
- modifica directamente costos, peritaje o decisiones económicas.
