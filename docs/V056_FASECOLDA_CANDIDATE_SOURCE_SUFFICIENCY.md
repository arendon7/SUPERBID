# SUPERBID v0.56 — Fasecolda Candidate Source Sufficiency Lifecycle

## 1. Problema que resuelve

v0.52 introdujo el gate correcto para confirmar manualmente un código Fasecolda: una homologación exacta solo puede existir después de evidencia humana estructurada, source-bound y auditable. v0.53–v0.55 redujeron el costo de comparar candidatos mediante pistas literales y el Candidate Discriminator Map, sin convertir automatización en evidencia.

Después de desplegar v0.55, el cuello de botella dejó de ser principalmente visual. El problema dominante es **si las fuentes permitidas contienen información suficiente para distinguir una versión exacta**.

v0.56 no relaja v0.52. Añade una capa anterior de suficiencia de fuente para evitar que el operador intente repetidamente completar un gate que las fuentes actuales no pueden satisfacer.

Guardrail canónico:

`CANDIDATE_SOURCE_TRIAGE_NOT_EVIDENCE_MATCH_OR_VALUATION`

Una clasificación o disposición de v0.56:
- no es evidencia v0.52;
- no es MATCH/CONFLICT humano;
- no confirma un código;
- no cambia Fasecolda efectivo;
- no escribe valoración, costos, ROI, max bid o decisión final;
- no es señal de compra.

## 2. Baseline productiva que justificó v0.56

Snapshot posterior a v0.55:
- 403 lotes totales;
- 236 `BLOCKED`;
- 167 `CLOSED`;
- 0 `READY`;
- 153 con `REVIEW_VALUATION`;
- dentro de valoración: 99 `CANDIDATE_RESOLUTION`, 39 `SEARCH_TERM_WORKFLOW`, 15 `YEAR_REFERENCE_REVIEW`;
- 0 resoluciones manuales de candidato;
- 0 evidencia candidate-resolution;
- los 99 estaban `UNREVIEWED`.

Composición automática de los 99:
- 92 `AMBIGUOUS`;
- 7 `MEDIUM`;
- candidate_count mínimo 1, máximo 11, promedio 4.28;
- distribución: 1×1, 2×24, 3×21, 4×14, 5×7, 6×16, 7×6, 8×9, 11×1.

### Fuentes registradas

- 99/99 tienen URL pública de subasta, permitida por v0.52;
- 76/99 tienen al menos un attachment;
- 54/99 tienen `PERITAJE`;
- 23/99 no tienen attachments;
- promedio de attachments: 2.59;
- attachments en estos casos:
  - 55 `PERITAJE` en 54 lotes;
  - 185 `DOCUMENTO` en 50 lotes;
  - 16 `ANEXO` en 16 lotes.

### Duplicados exactos bajo el gate v0.52

Usando exactamente:

`regexp_replace(upper(trim(description)), '[[:space:]]+', ' ', 'g')`

se encontraron:
- 18/99 lotes afectados;
- 36 grupos duplicados;
- 79 filas candidatas dentro de grupos duplicados;
- tamaño máximo de grupo: 3.

v0.56 no normaliza más agresivamente este criterio.

## 3. Suficiencia estructurada observada

Se midieron únicamente pistas deterministas equivalentes a v0.55:
- motor/cilindraje;
- transmisión;
- tracción;
- combustible.

Una dimensión solo se considera diferencial si hay por lo menos dos valores **conocidos y distintos** en el set candidato. Missing/unknown no crea diferencia.

Resultado sobre los 99:
- motor diferencia candidatos en 25 casos;
- transmisión en 50;
- tracción en 14;
- combustible en 0;
- 65/99 tienen al menos una diferencia estructurada;
- 34/99 no tienen diferencia estructurada detectable y dependen de trim/uso/equipamiento/u otra fuente.

Luego se preguntó algo distinto: ¿el título público declara un valor que apunte de forma única a un candidato dentro de una dimensión que sí varía?

Para cilindraje se preservó la tolerancia nominal de ±50 cc de v0.53. Resultado:
- título → motor único: 2 casos;
- título → transmisión única: 8;
- título → tracción única: 1;
- combustible: 0;
- total con al menos un proxy literal único: **11/99**.

Los 65 casos con diferencia estructurada se particionan exactamente en:
- 11 `TITLE_DISCRIMINATOR_AVAILABLE`;
- 54 `STRUCTURED_DIFFERENCE_SOURCE_UNRESOLVED`.

Los 34 restantes son `TRIM_OR_EXTERNAL_SOURCE_REQUIRED` salvo casos especiales.

### Coherencia de los 11 proxies

Se verificó que:
- 11/11 apuntan coherentemente a un solo código;
- 0/11 tienen proxies estructurados que apunten a códigos distintos;
- 11/11 tienen descripción target única bajo la normalización v0.52;
- en el snapshot actual, cada uno tiene exactamente una dimensión literal única;
- 11/11 tienen peritaje registrado.

Esto **no** significa que estén homologados. Solo justifica que entren directamente al gate humano v0.52 en vez de gastar una etapa adicional de triage.

## 4. El caso single-candidate que expuso una contradicción

Lote `4972494`:
- título: `VOLVO XC40 TP 1969 CC MOD. 2023, RP#1 PLACA: 9 Ubic.: MOSQUERA`;
- año 2023;
- búsqueda `VOLVO XC40`;
- único candidato: `09435010 — VOLVO XC40 PLUS B4 AT 2000CC TC`;
- score `0.3443`;
- `second_score=NULL`;
- `candidate_count=1`;
- estado automático `AMBIGUOUS`;
- peritaje registrado.

La función `fasecolda_match_lot` marca un único candidato como `HIGH` solo si `best_score >= 0.35`. Al estar en 0.3443, este caso cae al `else -> AMBIGUOUS` y recibe la nota genérica “Multiple Fasecolda versions…”, aunque no existen múltiples filas candidatas.

El estado de baja confianza puede ser razonable; lo incorrecto es enviarlo al workflow v0.52 de candidate resolution, porque ese gate exige por lo menos un MATCH no-lineal marcado `discriminating=true` **frente a una alternativa actual**. Con un solo candidato la condición es lógicamente imposible.

v0.56 no debilita el gate para acomodar este caso. Lo clasifica primero como:

`SINGLE_CANDIDATE_LOW_CONFIDENCE`

Debe pasar por source/identity/matcher triage antes de cualquier intento de homologación exacta.

## 5. Clases v0.56

### `SINGLE_CANDIDATE_LOW_CONFIDENCE`

Un solo candidato actual + automático AMBIGUOUS/MEDIUM. No puede usar el contrato discriminante v0.52 tal como está definido.

### `TITLE_DISCRIMINATOR_AVAILABLE`

Hay >=2 candidatos, una dimensión estructurada varía, el título declara un valor que coincide de forma única con un candidato, todos los proxies únicos convergen y la descripción target no está duplicada.

Ruta por defecto: `EVIDENCE_REVIEW`.

Esto solo omite triage redundante. El operador todavía debe llenar las seis dimensiones v0.52, citar fuentes registradas, mantener cero conflictos y confirmar explícitamente.

### `TITLE_PROXY_CONFLICT`

Dos o más proxies literales únicos apuntan a códigos distintos. No se elige ganador.

### `STRUCTURED_DIFFERENCE_SOURCE_UNRESOLVED`

Los candidatos difieren por motor/caja/tracción/combustible, pero el título no identifica uno de forma única.

### `TRIM_OR_EXTERNAL_SOURCE_REQUIRED`

Las dimensiones estructuradas conocidas no separan el set. Se requiere revisar trim, carrocería, uso, equipamiento u otra fuente permitida.

## 6. Correlación con attachments

Baseline:

| Clase empírica previa a v0.56 | Casos | Con peritaje | Con cualquier attachment | Con algún grupo de descripción duplicada |
|---|---:|---:|---:|---:|
| `TITLE_DISCRIMINATOR_AVAILABLE` | 11 | 11 | 11 | 2 lotes* |
| `STRUCTURED_DIFFERENCE_SOURCE_UNRESOLVED` | 54 | 31 | 36 | 6 |
| `NO_STRUCTURED_DIFFERENCE` | 34 | 12 | 29 | 10 |

\* Los 2 lotes contienen algún grupo duplicado en el set, pero el target literal único de los 11 casos no pertenece a un grupo duplicado; 11/11 targets son únicos.

La existencia de un peritaje no se interpreta automáticamente como suficiencia. v0.56 puede mostrarlo al humano, pero no hace OCR, extracción ni diagnóstico.

## 7. Fingerprint de evidencia operativa

Cada caso recibe `evidence_fingerprint` MD5 estable sobre datos que pueden cambiar la utilidad de una disposición:
- external_lot_id;
- título, marca, línea, año;
- automatic status;
- search term;
- best code, best score, second score;
- candidate count;
- snapshot estable de candidatos: code, model year, descripción normalizada, score y valor;
- URL pública del lote;
- snapshot estable de attachments: kind, name, URL, source;
- clase de source triage;
- target literal y dimensiones estructuradas/únicas.

No incluye timestamps de mera re-ejecución. Si cambia identidad, candidatos o fuentes, la disposición guardada deja de coincidir con el fingerprint y aparece como `STALE` automáticamente.

No se necesita cron para invalidar una decisión operativa.

## 8. Disposiciones humanas

Tabla current + histórico append-only.

Acciones:

### `ROUTE_TO_EVIDENCE_REVIEW`

El humano revisó fuentes actuales y considera que ameritan intentar el gate v0.52. **No confirma un código**. Está prohibida para `candidate_count < 2`, porque v0.52 exige una alternativa discriminada.

### `CONFIRM_CURRENT_SOURCES_INSUFFICIENT`

El humano revisó las fuentes del fingerprint actual y concluyó que no sustentan identidad exacta. Requiere nota >=20 caracteres.

Ruta: sigue económicamente bloqueado, pero no obliga a repetir el mismo trabajo hasta que el fingerprint cambie.

### `REQUEST_SOURCE_RESEARCH`

Hace explícito que se necesita una fuente adicional/actualizada y registrada.

### `REFER_IDENTITY_REVIEW`

La identidad pública del lote requiere revisión antes de seguir.

### `REQUEST_MATCHER_RECHECK`

Se sospecha que el snapshot de búsqueda/candidatos requiere re-evaluación.

### `CLEAR`

Retira la disposición actual y deja el caso nuevamente bajo su ruta calculada.

Ninguna acción escribe:
- `lot_fasecolda_matches`;
- `lot_fasecolda_manual_resolutions`;
- evidencia v0.52;
- Fasecolda effective;
- readiness;
- mercado;
- costos;
- max bid/ROI;
- decisión final.

## 9. Routing del workbench

Para AMBIGUOUS/MEDIUM unresolved:

1. disposición current `ROUTE_TO_EVIDENCE_REVIEW` → `CANDIDATE_RESOLUTION`;
2. disposición current `CONFIRM_CURRENT_SOURCES_INSUFFICIENT` → `CANDIDATE_SOURCE_INSUFFICIENT`;
3. `REQUEST_SOURCE_RESEARCH` → `CANDIDATE_SOURCE_RESEARCH`;
4. `REFER_IDENTITY_REVIEW` → `CANDIDATE_IDENTITY_REVIEW`;
5. `REQUEST_MATCHER_RECHECK` → `CANDIDATE_MATCHER_RECHECK`;
6. sin disposición + `TITLE_DISCRIMINATOR_AVAILABLE` → `CANDIDATE_RESOLUTION`;
7. resto → `CANDIDATE_SOURCE_TRIAGE`.

Con el snapshot que originó v0.56, antes de cualquier disposición humana, se espera aproximadamente:
- **11 `CANDIDATE_RESOLUTION`**;
- **88 `CANDIDATE_SOURCE_TRIAGE`**;
- 39 `SEARCH_TERM_WORKFLOW`;
- 15 `YEAR_REFERENCE_REVIEW`.

Readiness no cambia: los 153 continúan `REVIEW_VALUATION` hasta que exista una valoración realmente válida.

## 10. Edge dashboard

Nueva función:

`superbid-fasecolda-source-dashboard`

Auth:
- `dashboard_token_valid`;
- cookie `sb_fasecolda_source_session`;
- `HttpOnly; Secure; SameSite=Strict`;
- `verify_jwt=false` intencional por custom auth.

RPCs visibles:
- `dashboard_token_valid`;
- `dashboard_set_fasecolda_candidate_source_disposition_v56`.

No tiene RPC de confirmación candidata.

El detalle muestra:
- clasificación y ruta;
- fingerprint;
- candidatos actuales;
- diferencias estructuradas;
- target literal, si existe, marcado explícitamente como proxy read-only;
- URL de subasta;
- attachments/peritajes;
- visor PDF cuando aplica;
- histórico de disposiciones.

No usa OCR, PDF text extraction, visión o diagnóstico automático.

## 11. Compatibilidad

El Candidate Resolution Cockpit v0.52/v0.55 conserva su misma superficie de escritura. Su board ya filtra `workflow_target='CANDIDATE_RESOLUTION'`, heredado del workbench, por lo que la nueva clasificación reduce su cola sin modificar el formulario ni el gate.

El shim legacy `superbid-fasecolda-dashboard` deja de saltar directamente al cockpit y redirige a source-sufficiency, evitando que enlaces históricos omitan la nueva frontera.

## 12. Criterios de aceptación

v0.56 solo puede certificarse si:
1. migración aplica limpia;
2. RLS/permissions current/history/RPC son service_role-only;
3. helpers de pistas reproducen las reglas deterministas actuales;
4. source triage reporta el baseline esperado sin escribir datos;
5. single-candidate no puede usar `ROUTE_TO_EVIDENCE_REVIEW`;
6. RPC transaccional smoke demuestra cero writes fuera de disposition tables;
7. workbench conserva 153 `REVIEW_VALUATION` y redistribuye subworkflows sin crear READY;
8. cockpit mantiene exactamente sus tres RPCs v0.52;
9. nuevo dashboard compila con Deno y tiene solo auth + disposition RPC;
10. deployment se hace desde SHA Git inmutable;
11. postdeploy no aparecen manual resolutions/evidence falsos;
12. cualquier UAT HTTP/browser no ejecutable se registra como tal, nunca se fabrica.
