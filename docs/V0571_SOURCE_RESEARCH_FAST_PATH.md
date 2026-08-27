# SUPERBID v0.57.1 — Source Research Fast Path

## Problema observado en v0.57

La migración v0.57 fue aplicada correctamente y produjo la clasificación esperada de fuentes, pero el board global no se desplegó porque su consulta era demasiado costosa. La vista `dashboard_fasecolda_source_research_priority_v57` encadenaba:

`source triage v0.56 -> dashboard_fasecolda_resolution_queue -> dashboard_lot_current`

y además volvía a unir `dashboard_economic_readiness_current` para determinar si el caso era accionable.

En producción, el board global llegó a aproximadamente 31,2 s y ~1,0 M de buffer hits. El detalle exact-lot permaneció alrededor de 1,2–1,4 s, por lo que el problema era la expansión global del grafo y no el flujo humano puntual.

## Hallazgo de equivalencia

Se reconstruyó el cálculo v0.56 usando exclusivamente fuentes físicas necesarias:

- `auction_lots`
- último `auction_snapshots` por lote
- `lot_fasecolda_matches`
- `lot_fasecolda_manual_resolutions`
- `lot_fasecolda_candidates`
- `lot_attachments`
- `lot_fasecolda_candidate_source_dispositions`
- helpers deterministas de hints v0.56

La salida se comparó contra `dashboard_fasecolda_candidate_source_triage_v56` sobre los 176 casos `AMBIGUOUS`/`MEDIUM` no resueltos presentes en producción durante la investigación.

Resultado observado:

- 176 fast / 176 canonical
- 0 diferencias de set
- 0 diferencias de `source_triage_class`
- 0 diferencias de candidate count
- 0 diferencias de discriminadores estructurados
- 0 diferencias de targets literales
- 0 diferencias de grupos de descripción duplicada
- 0 diferencias de attachments/peritajes
- 0 diferencias de `evidence_fingerprint`
- 0 diferencias de disposition/current action
- 0 diferencias de `operational_route`
- 0 diferencias de `closes_at`

No se interpreta esta prueba como evidencia de identidad vehicular; es únicamente equivalencia del contrato de routing v0.56.

## Simplificación del gate accionable

Para este universo el match automático es `AMBIGUOUS` o `MEDIUM`, por lo que Fasecolda es el primer blocker de readiness mientras el lote no esté cerrado. De la definición vigente de `dashboard_economic_readiness_current` se deriva:

`next_action = REVIEW_VALUATION`

si y solo si:

`closes_at IS NULL OR closes_at > clock_timestamp()`

para estos casos no resueltos.

Se comparó el set simplificado contra el set canónico v0.57 en producción:

- simple: 82
- canonical: 82
- simple − canonical: 0
- canonical − simple: 0

El conteo había bajado desde los 88 observados al diseñar v0.57 porque algunas subastas cerraron durante el tiempo transcurrido; no se trató como regresión.

## Diseño v0.57.1

### `dashboard_fasecolda_candidate_source_triage_fast_v571`

Replica la semántica de triage/fingerprint/routing de v0.56 sin depender de:

- `dashboard_lot_current`
- `dashboard_fasecolda_resolution_queue`
- `dashboard_economic_readiness_current`
- mercado
- costos
- ROI

Es read-only y `service_role` only.

### `dashboard_fasecolda_source_research_queue_v571`

Combina el fast triage con el inventario metadata v0.57 y contiene únicamente casos actualmente accionables:

- `operational_route <> EVIDENCE_REVIEW`
- `closes_at IS NULL OR closes_at > clock_timestamp()`

La clasificación de metadata conserva exactamente la precedencia v0.57:

1. identidad primaria
2. identidad secundaria
3. peritaje/informe técnico con potencial de identidad
4. otra fuente registrada
5. adquisición de fuente externa

No existe cache, materialized view ni estado stale adicional.

## Benchmark previo al cambio

Sobre una consulta SQL equivalente al nuevo board, ejecutada contra datos productivos reales antes de crear las vistas:

- 82 filas accionables
- `Execution Time: 394.615 ms`
- `shared hit: 1,222`
- planning: 15.690 ms

Referencia del board v0.57 anterior:

- ~31,2 s
- ~1,0 M buffer hits

El benchmark es evidencia de performance de la consulta de investigación, no una garantía de latencia HTTP final.

## Edge Function

`superbid-fasecolda-source-dashboard` v0.57.1 separa explícitamente dos caminos:

- board global -> `dashboard_fasecolda_source_research_queue_v571`
- detalle exact-lot -> `dashboard_fasecolda_source_research_priority_v57`

La separación mantiene completion-safety del detalle y reduce el costo del board.

Los únicos RPC que la función puede invocar continúan siendo:

- `dashboard_token_valid`
- `dashboard_set_fasecolda_candidate_source_disposition_v56`

## Guardrails

v0.57.1 no añade OCR, parsing de PDF, visión, diagnóstico de anexos ni inferencia automática de hechos. Tampoco escribe:

- candidate-resolution evidence v0.52
- manual Fasecolda resolution
- Fasecolda automatic match
- mercado
- costos
- bids/max bid
- ROI
- decisión final

`SOURCE_RESEARCH_FAST_PATH_METADATA_ONLY_NOT_EVIDENCE_MATCH_OR_VALUATION`

La prioridad sigue significando únicamente **qué fuente abrir primero para investigación humana**, no qué candidato elegir.

## Gate de producción

Después de CI y merge se debe:

1. aplicar solamente la migración v0.57.1;
2. comparar fast triage vs v0.56 canónico nuevamente en producción;
3. comparar el set accionable v0.57.1 vs el set v0.57 canónico;
4. ejecutar `EXPLAIN (ANALYZE, BUFFERS)` sobre la vista creada;
5. desplegar `superbid-fasecolda-source-dashboard` con `verify_jwt=false` solo si la mejora se conserva;
6. releer metadata/source de la función desplegada;
7. comprobar cero escrituras de evidencia/resolución/economía atribuibles al despliegue;
8. no declarar UAT manual/browser que no haya sido ejecutado.
