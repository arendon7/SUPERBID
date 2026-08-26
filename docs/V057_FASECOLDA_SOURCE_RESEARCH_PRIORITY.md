# SUPERBID v0.57 — Fasecolda Source Research Priority

## Objetivo

v0.57 convierte el bloque `CANDIDATE_SOURCE_TRIAGE` de v0.56 en una cola de investigación humana mejor priorizada. La versión **no lee automáticamente documentos**, **no extrae hechos**, **no genera evidencia v0.52**, **no confirma códigos Fasecolda** y **no modifica valoración, readiness, max bid, ROI ni decisión de compra**.

La prioridad se calcula únicamente con metadata ya registrada de anexos (`kind`, `name`, `url`, `source`, `discovered_at`) y sirve para responder una pregunta operacional limitada:

> ¿Qué fuente registrada debería inspeccionar primero una persona, o hace falta conseguir una fuente externa de identidad?

Guardrail canónico:

`SOURCE_RESEARCH_PRIORITY_METADATA_ONLY_NOT_EVIDENCE_MATCH_OR_VALUATION`

## Baseline productiva después de v0.56

La vista canónica de valoración tenía **153 `REVIEW_VALUATION`**. Dentro de esos casos:

- 11 `CANDIDATE_RESOLUTION`;
- **88 `CANDIDATE_SOURCE_TRIAGE`**;
- 39 `SEARCH_TERM_WORKFLOW`;
- 15 `YEAR_REFERENCE_REVIEW`.

Los 88 casos de source triage se descomponen así:

| Clase v0.56 | Casos | Sin anexos | Con peritaje | Promedio candidatos |
| --- | ---: | ---: | ---: | ---: |
| `STRUCTURED_DIFFERENCE_SOURCE_UNRESOLVED` | 54 | 18 | 31 | 4.67 |
| `TRIM_OR_EXTERNAL_SOURCE_REQUIRED` | 33 | 5 | 11 | 4.03 |
| `SINGLE_CANDIDATE_LOW_CONFIDENCE` | 1 | 0 | 1 | 1.00 |

Totales relevantes:

- **23/88** no tienen anexos registrados;
- **43/88** tienen al menos un peritaje;
- los 88 acumulan anexos de tipo `PERITAJE`, `DOCUMENTO` y `ANEXO` provenientes de `superbid_product_attachments`.

## Hallazgo sobre calidad de los anexos

No todo `DOCUMENTO` tiene valor para identidad. En producción aparecen grupos repetidos de documentos administrativos como formularios SAGRILAFT/SARLAFT, habeas data, contratos, actas y formatos genéricos. También aparecen fuentes cuyo nombre sí sugiere potencial de identidad o especificaciones, por ejemplo:

- matrícula / tarjeta de propiedad;
- certificado de tradición o libertad;
- licencia o registro de tránsito;
- SOAT;
- RTM / revisión técnico-mecánica;
- TP;
- informe técnico;
- peritaje / inspección.

El nombre del archivo **no prueba su contenido**. v0.57 usa esa metadata exclusivamente para navegación/prioridad de revisión humana.

## Simulación previa sobre los 88 casos

Antes de implementar la vista v0.57 se ejecutó un clasificador prospectivo exclusivamente sobre metadata. El resultado fue:

- **41 casos** con documentos cuyo nombre sugiere identidad/especificaciones;
- **23 casos** sin esos documentos pero con peritaje/inspección;
- **23 casos** sin anexos, por lo que requieren adquirir o registrar una fuente externa;
- **1 caso** con otra fuente registrada no clasificada como identidad/peritaje.

La división exacta entre identidad primaria y secundaria se certificará sobre la vista v0.57 después de aplicar la migración.

## Taxonomía v0.57

`fasecolda_source_metadata_role_v57(kind,name)` clasifica metadata en:

1. `IDENTITY_PRIMARY`
   - matrícula;
   - tarjeta de propiedad;
   - certificado de tradición/libertad;
   - licencia de tránsito;
   - registro vehicular.
2. `IDENTITY_SECONDARY`
   - SOAT;
   - RTM / revisión técnica;
   - TP;
   - informe técnico.
3. `CONDITION_IDENTITY_POTENTIAL`
   - `kind=PERITAJE`;
   - nombre que indica peritaje o inspección.
4. `OTHER_REGISTERED`
   - fuente registrada no reconocida en las categorías anteriores.
5. `ADMINISTRATIVE_GENERIC`
   - SAGRILAFT/SARLAFT;
   - habeas data;
   - contrato de compraventa genérico;
   - acta de compromiso;
   - prevención LAFT;
   - formatos B/C genéricos.

Ranks de metadata:

- identidad primaria: 10;
- identidad secundaria: 20;
- peritaje/inspección: 30;
- otra fuente: 40;
- administrativa genérica: 90.

## Vistas

### `dashboard_fasecolda_attachment_research_inventory_v57`

Agrega por lote:

- conteos por rol de metadata;
- primera fuente a revisar por rank + id estable;
- inventario JSON completo ordenado por metadata.

Es read-only y `service_role`-only.

### `dashboard_fasecolda_source_research_priority_v57`

Extiende el source triage v0.56 con:

- estado readiness;
- `source_research_actionable`;
- inventario/contadores de fuentes;
- `research_route`;
- `research_rank`;
- razón operacional;
- guardrail metadata-only.

Rutas:

- `REVIEW_IDENTITY_PRIMARY_SOURCE`;
- `REVIEW_IDENTITY_SECONDARY_SOURCE`;
- `REVIEW_PERITAJE_FOR_IDENTITY_FACTS`;
- `REVIEW_OTHER_REGISTERED_SOURCE`;
- `ACQUIRE_EXTERNAL_IDENTITY_SOURCE`.

La cola principal solo muestra `source_research_actionable=true`, definido como:

- readiness `REVIEW_VALUATION`; y
- ruta v0.56 distinta de `EVIDENCE_REVIEW`.

El detalle por lote sigue siendo completion-safe y puede abrir un caso exacto aunque deje de estar accionable.

## Dashboard v0.57

`superbid-fasecolda-source-dashboard` conserva el modelo de autorización privado de v0.56:

- `dashboard_token_valid`;
- cookie `sb_fasecolda_source_session`;
- `HttpOnly; Secure; SameSite=Strict`;
- `service_role` únicamente server-side;
- `verify_jwt=false` intencional por auth custom.

La pantalla:

- ordena casos por `research_rank` y cierre;
- muestra conteos de identidad primaria/secundaria, peritaje potencial, administrativos y otros;
- marca la primera fuente por metadata;
- abre únicamente URL pública del lote o anexos ya registrados;
- puede preseleccionar la primera fuente para ahorrar navegación;
- **no interpreta el contenido de la fuente**;
- no usa OCR, visión, PDF text extraction ni diagnóstico automático.

La preselección es navegación. No constituye evidencia ni preselección de candidato.

## Autoridad de escritura

v0.57 **no agrega ningún RPC de escritura**.

El dashboard conserva exactamente los dos RPC visibles de v0.56:

1. `dashboard_token_valid`;
2. `dashboard_set_fasecolda_candidate_source_disposition_v56`.

Las disposiciones siguen siendo operativas. No escriben candidate evidence, manual resolution, effective match ni valoración.

## Frontera con el gate v0.52

v0.52 permanece como única ruta de confirmación candidata. Para `p_mark_reviewed=true` exige, entre otras condiciones:

- las seis dimensiones completas;
- `line_identity=MATCH`;
- cero `CONFLICT`;
- al menos un `MATCH` explícitamente discriminante adicional a line identity;
- source URL HTTP(S) que pertenezca al lote;
- notas humanas;
- candidato actual, año compatible, valor vigente y identity guard.

Solo ese workflow puede llegar a una resolución manual. v0.57 no escribe ni prellena esos estados.

## Riesgo mitigado

v0.56 separó source sufficiency de candidate resolution, pero el dashboard source mostraba también casos no accionables/cerrados porque la vista base contiene todo AMBIGUOUS/MEDIUM no resuelto. v0.57 añade `source_research_actionable` usando readiness para mantener la cola operativa limpia, mientras conserva detalle exact-lot completion-safe.

## Criterios de aceptación

- CI Python completamente verde.
- Todas las Edge Functions pasan `deno check`.
- Metadata helpers y vistas son `service_role`-only.
- Cola accionable reproduce los 88 casos de v0.56, salvo cambios naturales de subasta/datos ocurridos entre snapshots.
- La suma por `research_route` coincide con el universo accionable.
- No se crean filas en evidence/manual-resolution/source-disposition por aplicar la migración o desplegar Edge.
- El source dashboard mantiene exactamente auth + disposition RPC.
- No se afirma UAT manual/browser sin ejecutarlo realmente.
