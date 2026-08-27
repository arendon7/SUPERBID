# SUPERBID v0.58 — Fasecolda Evidence Handoff

## Objetivo

Reducir la fricción entre la investigación humana de fuentes (v0.57.1) y el gate de evidencia exacta de candidato (v0.52), sin crear un segundo sistema de homologación ni ampliar autoridad automática.

v0.58 tiene dos cambios operativos:

1. un fast path exclusivo para el **board** Candidate Resolution;
2. continuidad visual de la **fuente que la persona ya estaba inspeccionando** al pasar de Source Research al cockpit v0.52.

El detalle exact-lot, las seis dimensiones de evidencia, la validación source-bound, la resolución manual y el hardening trigger siguen siendo v0.52.

## Evidencia productiva previa

El 27 de agosto de 2026 UTC / 26 de agosto hora Colombia se midió el estado productivo antes de implementar v0.58.

### Universo activo

- `REVIEW_VALUATION`: 151 casos en el snapshot observado.
- Dentro de ellos: 84 `AMBIGUOUS`, 7 `MEDIUM`, 31 `UNMATCHED`, 29 sin match efectivo en ese snapshot.
- En una medición posterior, por cierres naturales, quedaron 88 `AMBIGUOUS/MEDIUM` activos.
- 77 permanecían en source research.
- 11 tenían `operational_route=EVIDENCE_REVIEW` y `workflow_target=CANDIDATE_RESOLUTION`.
- Los 11 estaban `UNREVIEWED`; 0 DRAFT; 0 REVIEWED.

Los 11 lotes observados fueron:

`4969325`, `4972485`, `4972661`, `4973771`, `4973772`, `4973775`, `4973776`, `4973792`, `4978221`, `4978226`, `4978233`.

### Equivalencia de cola

Se comparó el board canónico v0.52 con una derivación desde el fast triage v0.57.1:

- canónico: 11;
- fast: 11;
- diferencia simétrica: 0.

La derivación fast usada fue:

- `operational_route='EVIDENCE_REVIEW'`;
- subasta viva: `closes_at is null or closes_at > clock_timestamp()`.

Esto es deliberadamente routing, no evidencia.

### Rendimiento

Medición SQL con timestamp materializado, sobre producción:

- board canónico `dashboard_fasecolda_candidate_resolution_cockpit_v52`: **9074.338 ms** para 11 casos;
- set equivalente sobre `dashboard_fasecolda_candidate_source_triage_fast_v571`: **4.268 ms**;
- exact-lot v0.52 (`external_lot_id=4969325`): **8.494 ms**.

Conclusión: el costo problemático está en el board global, no en el detalle exact-lot. Por eso v0.58 no reemplaza el detalle v0.52.

## Fast candidate queue v0.58

Nueva vista:

`dashboard_fasecolda_candidate_resolution_queue_v58`

Fuentes de datos:

- `dashboard_fasecolda_candidate_source_triage_fast_v571`;
- `lot_fasecolda_candidate_resolution_evidence` únicamente para mostrar estado DRAFT/REVIEWED y sus contadores.

No depende de:

- `dashboard_economic_readiness_current`;
- `dashboard_fasecolda_resolution_queue`;
- `dashboard_fasecolda_valuation_workbench`;
- mercado;
- costos;
- ROI;
- decisión final.

La vista es `service_role` only.

### Routing provenance

Se expone `evidence_route_origin`:

- `TITLE_DISCRIMINATOR`: la ruta ya era EVIDENCE_REVIEW por discriminador literal determinista;
- `HUMAN_SOURCE_DISPOSITION`: una disposición humana vigente `ROUTE_TO_EVIDENCE_REVIEW` movió el trabajo al gate.

Ninguno de los dos valores constituye evidencia de que un código sea correcto.

## Handoff de fuente

Source Research ya permite inspeccionar una fuente registrada en un viewer. v0.58 conserva ese contexto al pasar al Candidate Cockpit.

Reglas:

1. la URL se normaliza a HTTP(S);
2. Source Research vuelve a verificar que sea la URL pública del lote o un anexo registrado para ese mismo lote antes de entregarla al cockpit;
3. el cockpit vuelve a verificar la misma condición antes de mostrarla;
4. una URL no registrada se ignora;
5. el contexto puede sobrevivir selección de candidato y guardado DRAFT solo como query context;
6. el viewer nunca alimenta automáticamente el formulario.

## Lo que el handoff NO hace

La fuente en contexto **no**:

- selecciona candidato;
- marca `MATCH`, `CONFLICT` o `NOT_STATED`;
- copia `observed_value`;
- selecciona `source_url` en ninguna dimensión;
- marca `discriminating`;
- escribe `evidence_note`;
- genera resumen;
- ejecuta OCR o parsing;
- crea evidencia REVIEWED;
- crea resolución manual;
- cambia Fasecolda efectivo;
- cambia mercado, costos, bid, ROI o decisión final.

## Autoridad que permanece intacta

Source Research conserva únicamente:

- `dashboard_token_valid`;
- `dashboard_set_fasecolda_candidate_source_disposition_v56`.

Candidate Cockpit conserva únicamente:

- `dashboard_token_valid`;
- `dashboard_save_fasecolda_candidate_resolution`;
- `dashboard_clear_fasecolda_candidate_resolution_v52`.

La confirmación REVIEWED sigue exigiendo el contrato v0.52 completo: 6/6 dimensiones, `line_identity=MATCH`, cero conflictos, por lo menos un MATCH no-lineal explícitamente discriminante, fuente válida por dimensión y confirmación humana explícita.

## Guardrail

`CANDIDATE_EVIDENCE_FAST_QUEUE_ROUTING_NOT_EVIDENCE_MATCH_OR_BUY_SIGNAL`

El fast path y el contexto de fuente reducen latencia y navegación. No aumentan autoridad semántica.
