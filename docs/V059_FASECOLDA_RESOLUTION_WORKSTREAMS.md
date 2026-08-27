# SUPERBID v0.59 — Fasecolda Resolution Workstreams

## Objetivo

v0.59 introduce un control plane de routing Fasecolda rápido y explícitamente read-only. Su función es responder una sola pregunta operacional: **¿qué workflow humano debe abrirse a continuación para este lote?**

No crea homologaciones, evidencia, valoraciones, pujas, ROI, decisiones finales ni señales de compra.

Guardrail canónico:

`FASECOLDA_RESOLUTION_WORKSTREAM_ROUTING_NOT_MATCH_VALUATION_OR_BUY_SIGNAL`

## Problema observado

Antes de v0.59, `superbid-fasecolda-workbench` consultaba `dashboard_fasecolda_valuation_workbench`. Esa vista es útil como capa canónica/auditable, pero para decidir routing atraviesa dependencias de readiness/economía y varios workflows especializados.

Benchmark de producción previo al cambio:

- Workbench canónico: ~2.185 s de ejecución para 145 casos activos.
- La finalidad del board no requiere cálculo económico.

## Equivalencia antes de implementar

Se construyó y ejecutó en producción un CTE fast sin persistencia y se comparó por `lot_id` + `external_lot_id` con el Workbench canónico.

Resultado en el snapshot de certificación:

- fast: 145 casos
- canónico: 145 casos
- diferencia simétrica: **0**

Distribución:

| Workstream | Casos |
|---|---:|
| `CANDIDATE_EVIDENCE` | 11 |
| `SOURCE_REGISTERED_REVIEW` | 45 |
| `CATALOG_INDISTINGUISHABLE` | 15 |
| `SOURCE_ACQUISITION` | 17 |
| `SEARCH_REVIEW` | 50 |
| `YEAR_REVIEW` | 7 |

Los conteos son evidencia del snapshot previo al merge, no constantes de negocio.

## Arquitectura

La nueva vista es:

`dashboard_fasecolda_resolution_workstreams_v59`

### Candidate / Source

Reutiliza `dashboard_fasecolda_candidate_source_triage_fast_v571` y consulta anexos únicamente por los lotes candidatos mediante `LATERAL` sobre `lot_attachments`.

Conserva como contexto:

- `source_operational_route`
- `source_disposition_action`
- `source_disposition_status`

La autoridad sobre ese lifecycle sigue en `superbid-fasecolda-source-dashboard`.

### Search / Year

El routing se deriva directamente de:

- `auction_lots`
- `lot_fasecolda_effective_current`
- último `auction_snapshots` mediante `LATERAL ... ORDER BY observed_at DESC LIMIT 1`
- `fasecolda_suggest_search_term(title)`

El board no consulta readiness ni economía.

El lifecycle detallado Year permanece en el dashboard especializado; v0.59 solo decide si el caso debe abrir Search o Year.

## Catalog indistinguishable

Los casos con `duplicate_description_group_count > 0` se separan como `CATALOG_INDISTINGUISHABLE`.

Esto evita una falla operacional importante: hacer revisar un PDF como si pudiera distinguir candidatos cuyas descripciones Fasecolda normalizadas son indistinguibles. La acción es revisar catálogo/matcher o enriquecer candidatos, no inventar evidencia discriminante.

## Prioridad

1. `CANDIDATE_EVIDENCE` — rank 10
2. `SOURCE_REGISTERED_REVIEW` — rank 20
3. `SEARCH_REVIEW` — rank 30
4. `YEAR_REVIEW` — rank 40
5. `SOURCE_ACQUISITION` — rank 60
6. `CATALOG_INDISTINGUISHABLE` — rank 90

El rank es de trabajo operacional, no de atractivo económico.

## Rendimiento medido antes de persistir la vista

- primera unión fast con inventario global de anexos: ~273 ms
- Candidate/Source con lookup lateral por lote: ~141 ms
- board fast completo de 145 filas: **~157 ms**

Comparado con ~2.185 s del Workbench canónico, el prototipo fast fue aproximadamente 13.9x más rápido.

Estos valores son benchmarks puntuales; deben recertificarse después de aplicar la migración.

## Edge Function

`superbid-fasecolda-workbench` pasa a:

- una sola consulta a `dashboard_fasecolda_resolution_workstreams_v59`;
- filtros por workstream;
- exact-lot 5–12 dígitos preservado en login y navegación;
- auth únicamente mediante `dashboard_token_valid`;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- render server-side, sin JavaScript cliente;
- cero RPCs de negocio.

Los destinos especializados son:

- Candidate Evidence → Candidate Cockpit
- Registered Source / Acquisition / Catalog → Source Dashboard
- Search Review → Search Dashboard
- Year Review → Year Dashboard

## Seguridad y autoridad

La vista nueva:

- revoca acceso a `public`, `anon` y `authenticated`;
- concede `SELECT` únicamente a `service_role`;
- no contiene DML ni RPCs de escritura.

El Workbench canónico histórico no se elimina ni se modifica. Permanece disponible como referencia de auditoría y para verificar equivalencia cuando sea necesario.

## Gates de release

Antes de producción deben cumplirse:

1. pytest completo verde;
2. Edge `deno check` verde;
3. branch `behind_by=0`;
4. migración aplicada una sola vez;
5. equivalencia post-migración contra Workbench canónico;
6. permisos service-role-only;
7. benchmark post-migración;
8. zero-write antes y después del deploy;
9. deploy de `superbid-fasecolda-workbench` desde SHA fusionado inmutable;
10. readback del artefacto Edge live.
