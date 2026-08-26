# SUPERBID v0.55 — Fasecolda Candidate Discriminator Map

## Problema

Después de v0.54, el mayor cuello de botella de due diligence continúa en Fasecolda:

- 403 lotes en la cola global;
- 236 `BLOCKED`;
- 167 `CLOSED`;
- 0 `READY`;
- 153 casos con `REVIEW_VALUATION`;
- dentro de ellos, 99 `CANDIDATE_RESOLUTION`, 39 `SEARCH_TERM_WORKFLOW` y 15 `YEAR_REFERENCE_REVIEW`.

v0.54 atacó el workflow de búsqueda. v0.55 se concentra exclusivamente en los 99 casos de candidate resolution.

El problema ya no es obtener candidatos. Es comparar versiones cercanas con suficiente claridad para que una persona pueda dirigir la investigación de evidencia sin confundir score, descripción o heurística con homologación.

## Baseline productiva

Los 99 casos candidate-resolution estaban completamente vírgenes al diseñar v0.55:

- 99/99 `UNREVIEWED`;
- 99/99 `UNRESOLVED`;
- 99/99 con `evidence_complete_count=0`;
- 99/99 sin `evidence_source_urls`;
- 92 `AMBIGUOUS`;
- 7 `MEDIUM`.

La mayoría de los márgenes fuzzy son mínimos. En grupos AMBIGUOUS de 2–8 candidatos, el margen medio entre primero y segundo está normalmente entre 0.00 y 0.05. Por tanto, aumentar la autoridad del score automático sería conceptualmente incorrecto.

### Diferencias estructuradas reales

Auditando los candidatos actuales con las mismas reglas literales de v0.53:

- 65/99 casos tienen al menos una dimensión estructurada que varía entre candidatos;
- motor/cilindraje discrimina en 25 casos;
- transmisión discrimina en 50;
- tracción discrimina en 14;
- 34/99 no tienen ninguna diferencia detectable en esas dimensiones estructuradas.

Distribución por cantidad de dimensiones estructuradas variables:

- 34 casos: 0;
- 44 casos: 1;
- 18 casos: 2;
- 3 casos: 3.

Una dimensión se considera variable únicamente cuando existen por lo menos dos valores **conocidos y distintos** en el set. `null`/ausencia de dato nunca se transforma en diferencia.

### Trim, uso y cuerpo

Las descripciones productivas muestran diferencias relevantes que no caben solo en motor/caja/tracción:

- `CARGO` vs `ZEN` vs `INTENS OUTSIDER`;
- `BUS` vs `LWB`;
- `SPORT` vs `XS` vs `GR`;
- generaciones, trims, cabina, uso, puertas y equipamiento.

Por eso v0.55 agrega también deltas **literales** entre descripciones, sin inferencia semántica.

### Indistinguibilidad real

La auditoría encontró:

- 18/99 casos con al menos un grupo de dos o más candidatos cuya descripción normalizada es idéntica;
- 79 filas candidatas pertenecen a esos grupos;
- 1 caso no tiene ningún candidato con descripción única;
- 14 casos tienen exactamente un candidato con descripción única;
- 84 tienen dos o más candidatos con descripción única.

Una descripción duplicada no es una razón para seleccionar uno de los códigos. Es evidencia de que el dataset disponible **no distingue** esos códigos por texto. El gate v0.52 continúa bloqueando una confirmación exacta arbitraria.

## Invariante v0.55

`CANDIDATE_DISCRIMINATOR_MAP_NOT_EVIDENCE_OR_RECOMMENDATION`

El mapa:

- no es evidencia;
- no es homologación;
- no es ranking;
- no crea score;
- no recomienda candidato;
- no preselecciona código;
- no marca dimensiones humanas como `MATCH`;
- no marca automáticamente el flag humano `discriminating`;
- no escribe base de datos;
- no cambia Fasecolda efectivo;
- no cambia bid, max bid, ROI, costos, mercado ni decisión final.

## Arquitectura

### Helper puro

Archivo:

`supabase/functions/superbid-fasecolda-candidate-cockpit/candidate_discriminators.ts`

Reutiliza `extractVehicleIdentityHints` de v0.53 y no duplica reglas de extracción.

No contiene:

- `fetch`;
- acceso a `Deno.env`;
- REST/RPC;
- service-role;
- mutaciones;
- ranking o winner.

### Structured discriminator map

Dimensiones:

- `engine_cc`;
- `transmission`;
- `drivetrain`;
- `fuel`.

Una dimensión entra al mapa solo si el conjunto contiene dos o más valores conocidos distintos. Un candidato sin valor conocido no introduce una diferencia falsa.

### Literal delta tokens

Cada descripción se normaliza de forma determinista:

- Unicode sin diacríticos;
- mayúsculas;
- caracteres no alfanuméricos convertidos a separadores;
- espacios colapsados;
- tokens deduplicados conservando orden.

Para cada candidato se muestran únicamente tokens presentes en ese candidato que no aparecen en todos los candidatos del set.

Esto permite hacer visibles palabras como `CARGO`, `ZEN`, `OUTSIDER`, `LWB`, `SPORT`, etc. sin afirmar qué significan jurídicamente o técnicamente.

El resultado está acotado a máximo 12 tokens por candidato.

### Duplicate-description groups

El helper agrupa candidatos cuya descripción normalizada es idéntica y expone:

- tamaño del grupo;
- cantidad de grupos duplicados;
- cantidad de candidatos dentro de grupos duplicados;
- flag `indistinguishableByDescription`.

La UI lo comunica como incapacidad de distinguir por descripción, no como indicación de cuál código escoger.

## Integración en el cockpit

v0.55 modifica únicamente `superbid-fasecolda-candidate-cockpit`.

No agrega vista SQL ni query por caso al board. El mapa se calcula en memoria solamente cuando el detalle ya cargó el set canónico de candidatos.

En detalle aparece:

1. resumen “Mapa de diferencias actuales”;
2. chips de dimensiones estructuradas que sí varían;
3. advertencia si hay descripciones indistinguibles;
4. por candidato, valor de cada dimensión estructurada variable;
5. por candidato, tokens literales diferenciales;
6. advertencia de duplicate group;
7. orientación read-only para el candidato seleccionado.

La orientación del candidato seleccionado se renderiza **fuera del `<form>` de evidencia**.

El mapa no crea campos `name=`, no entra en `FormData` y no forma parte de `p_dimensions`.

## Gate humano v0.52 intacto

La confirmación REVIEWED sigue exigiendo exactamente el contrato v0.52:

- 6/6 dimensiones humanas completas;
- `line_identity=MATCH`;
- cero `CONFLICT`;
- al menos un MATCH no-lineal marcado manualmente como discriminante;
- fuente permitida y ligada al lote;
- fundamento humano;
- candidato todavía vigente;
- año válido;
- valor Fasecolda utilizable;
- identity guard;
- bloqueo de candidatos indistinguibles por descripción.

v0.55 no prellena ningún estado, valor observado, fuente, fundamento ni checkbox.

## Selección de candidato intacta

El candidato que entra al formulario continúa determinado exclusivamente por:

1. `?candidate=<code>` solicitado explícitamente por el operador; o
2. un snapshot v0.52 ya persistido para el mismo lote cuando no existe query explícito.

No participan:

- `automatic_best_code`;
- `automatic_best_score`;
- rank;
- hints v0.53;
- structured discriminator map;
- literal deltas;
- cantidad de tokens;
- ausencia/presencia de duplicados.

## Autoridad

No hay migración v0.55.

La superficie RPC del cockpit permanece exactamente:

- `dashboard_token_valid`;
- `dashboard_save_fasecolda_candidate_resolution`;
- `dashboard_clear_fasecolda_candidate_resolution_v52`.

No se agrega autoridad económica ni de compra.

## Tests

### Deno

`candidate_discriminators_test.ts` valida:

- guardrail y límite de 12 tokens;
- dimensión estructurada solo con dos valores conocidos distintos;
- unknown no crea diferencia artificial;
- deltas literales de trim/uso;
- agrupación de descripciones indistinguibles;
- preservación del orden de candidatos;
- determinismo;
- límite de tokens;
- combustible como discriminador solo con valores conocidos distintos;
- ausencia de winner/recommendation/score en el contrato del mapa.

El gate v0.54 ya descubre automáticamente todos los `*_test.ts`, por lo que estos tests se ejecutan en CI sin ampliar un allowlist.

### Pytest

La suite v0.55 congela:

- pureza del helper;
- falta de autoridad REST/RPC;
- no ranking/recommendation;
- mapa fuera del payload humano;
- selección exacta de candidato intacta;
- misma autoridad RPC;
- cero migration;
- versión 0.55.0;
- ausencia de autoridad económica.

## Release gates

Antes de merge:

1. full historical pytest suite PASS;
2. v0.55 regression suite PASS;
3. todos los Edge `index.ts` pasan `deno check`;
4. todos los `*_test.ts` Deno pasan;
5. branch `behind_by=0`;
6. revisión de diff sin migration ni autoridad nueva.

Antes de producción:

1. snapshot de readiness/workflows;
2. snapshot de manual resolutions/evidence;
3. deploy desde SHA inmutable de `main`;
4. runtime files únicamente `index.ts`, `identity_hints.ts` y `candidate_discriminators.ts`;
5. `verify_jwt=false` solo porque el cockpit conserva auth custom con `dashboard_token_valid`;
6. readback de función ACTIVE;
7. postdeploy zero-write audit;
8. no reclamar browser UAT si el entorno no puede resolver DNS.

## No objetivos

v0.55 no:

- interpreta PDFs;
- extrae evidencia de anexos;
- escoge un candidato;
- resuelve duplicate-description groups;
- calcula un nuevo score;
- convierte delta literal en `MATCH`;
- convierte hint en evidencia;
- escribe resolución manual automáticamente;
- modifica readiness por sí solo;
- genera buy signal.
