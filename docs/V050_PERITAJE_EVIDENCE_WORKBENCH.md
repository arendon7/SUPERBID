# v0.50 — Peritaje Evidence Workbench

## Diagnóstico productivo

Después de cerrar v0.49, la primera acción de los 248 lotes activos bloqueados quedó distribuida así:

- 161 `REVIEW_VALUATION`;
- 59 `REVIEW_PERITAJE`;
- 24 `REVIEW_CONDITION_RISK`;
- 4 `REVIEW_COMMISSION`.

Los 59 casos `REVIEW_PERITAJE` tienen una propiedad especialmente favorable para operación:

- 59/59 ya tienen un peritaje público;
- cada uno tiene exactamente un PDF público detectado;
- la fuente proviene de `superbid_product_attachments`;
- no existía ninguna revisión de peritaje guardada todavía, ni DRAFT ni REVIEWED.

Por tanto el cuello de botella no es conseguir el documento: es convertir su lectura en evidencia humana estructurada y auditable sin fabricar un diagnóstico.

## Problema del flujo anterior

v0.29 ya protegía correctamente varias fronteras:

- revisión humana explícita;
- 8 dimensiones de riesgo;
- rango de reparación low/base/high;
- no transferencia automática a costos;
- `MANUAL_PERITAJE_REVIEW_NOT_AUTOMATED_DIAGNOSIS`.

Pero la evidencia quedaba principalmente en:

- el valor de riesgo seleccionado;
- una nota general libre;
- el enlace al PDF en otra parte del detalle general.

Esto deja tres fricciones:

1. el operador alterna entre PDF y formulario;
2. no existe evidencia específica por cada dimensión;
3. una clasificación `LOW`, `HIGH` o `NOT_EVALUABLE` no explica por sí misma qué parte del PDF la sustenta.

## Objetivo v0.50

Crear un workbench especializado que permita revisar un peritaje público manteniendo PDF, clasificación y fundamento en el mismo caso.

La release **no** intenta extraer o diagnosticar automáticamente el estado del vehículo.

Guardrail principal:

`MANUAL_PERITAJE_EVIDENCE_NOT_AUTOMATED_DIAGNOSIS_OR_BUY_SIGNAL`

## Contrato de REVIEWED

Un peritaje solo puede quedar REVIEWED si existe:

1. `external_lot_id` válido;
2. PDF `PERITAJE` que realmente pertenezca al lote;
3. las ocho dimensiones estructuradas;
4. un riesgo permitido por dimensión;
5. una nota de evidencia de al menos 10 caracteres por dimensión;
6. low/base/high de reparación;
7. `low <= base <= high`;
8. fundamento del rango de reparación de al menos 20 caracteres.

Las dimensiones son:

- `mechanical`;
- `transmission`;
- `body`;
- `safety`;
- `electrical`;
- `tires`;
- `documentation`;
- `missing_parts`.

Riesgos permitidos:

- `LOW`;
- `MEDIUM`;
- `HIGH`;
- `CRITICAL`;
- `NOT_EVALUABLE`.

`NOT_EVALUABLE` es deliberado: cuando el PDF no permite concluir, el sistema obliga a documentar esa limitación en lugar de inventar certeza.

## Modelo de evidencia

### `lot_peritaje_evidence_reviews`

Estado actual, uno por lote.

Contiene:

- PDF fuente;
- JSON `dimensions`;
- `overall_risk`;
- completitud 0–8;
- rango low/base/high;
- fundamento del rango;
- notas generales;
- `reviewed_at`;
- interpretación fija.

### `lot_peritaje_evidence_review_history`

Registro append-only de cada DRAFT o REVIEWED.

No se elimina ni reemplaza el histórico v0.29. El nuevo histórico complementa la trazabilidad existente.

Ambas tablas:

- RLS habilitado;
- sin acceso `public`, `anon` o `authenticated`;
- acceso backend por `service_role`.

## Protección de la revisión canónica

v0.50 agrega `trg_peritaje_evidence_review_gate_v50` sobre `lot_peritaje_reviews`.

Si `reviewed_at` es no nulo, el trigger exige:

- un registro de evidencia v0.50 REVIEWED para el mismo lote;
- mismo PDF fuente;
- mismos 8 riesgos;
- mismo `overall_risk`;
- mismo low/base/high.

Así el flujo legacy puede seguir existiendo para borradores/consulta, pero no puede crear una revisión cerrada que contradiga o omita la evidencia v0.50.

## RPC

`dashboard_save_peritaje_evidence_review`

Es la única autoridad nueva de escritura de negocio de esta wave.

Puede escribir únicamente:

- evidencia de peritaje v0.50;
- histórico de evidencia;
- espejo canónico de `lot_peritaje_reviews`;
- histórico canónico v0.29.

No puede escribir:

- costos del lote;
- transferencia peritaje → costos;
- mercado;
- Fasecolda;
- puja;
- puja máxima;
- ROI;
- decisión final;
- recomendación de compra.

Devuelve explícitamente:

- `diagnosis_generated=false`;
- `buy_signal=false`;
- `cost_fields_modified=false`;
- `economic_fields_modified=false`.

## Workbench

Edge Function:

`superbid-peritaje-evidence-workbench`

### Cola

Por defecto muestra únicamente:

`next_action = REVIEW_PERITAJE`

Puede ampliarse a todos los lotes activos con peritaje o al histórico completo.

### Detalle exacto

Ruta:

`/lots/<external_lot_id>`

Incluye:

- PDF público embebido;
- enlace de apertura externa como fallback;
- selección explícita del PDF fuente;
- ocho tarjetas de evidencia;
- riesgo por dimensión;
- nota de evidencia por dimensión;
- página/referencia opcional;
- low/base/high;
- fundamento del rango;
- notas generales;
- histórico append-only.

Si solo existe un PDF, se preselecciona como **fuente documental**, nunca como conclusión.

## Completion safety

El detalle consulta el lote exacto en `dashboard_peritaje_evidence_workbench_v50`, no únicamente la cola pendiente.

Por tanto puede seguir explicando el caso después de REVIEWED.

Después de un REVIEWED exitoso se vuelve a:

`superbid-readiness-dashboard?lot=<external_lot_id>`

Readiness recalcula el siguiente blocker canónico.

## Integración Due Diligence

Desde v0.50:

`REVIEW_PERITAJE` → `superbid-peritaje-evidence-workbench/lots/<id>`

El detalle legacy continúa disponible como consulta secundaria para preservar continuidad, pero ya no es el CTA primario para resolver `PERITAJE_NOT_REVIEWED`.

Guardrail de routing:

`PERITAJE_EVIDENCE_ROUTING_NOT_BUY_SIGNAL`

## Seguridad

- contexto permitido: `external_lot_id` numérico de 5–12 dígitos;
- no `return_to`;
- no `redirect_uri`;
- no `redirect_url`;
- redirects construidos server-side;
- cookie propia `HttpOnly; Secure; SameSite=Strict`;
- `verify_jwt=false` solo porque el dashboard usa autenticación privada custom existente;
- URLs de PDF renderizadas únicamente si son `http` o `https`.

RPCs visibles desde el workbench:

- `dashboard_token_valid`;
- `dashboard_save_peritaje_evidence_review`.

## Fronteras económicas

El rango de reparación capturado en el workbench no modifica `repair_cop`.

La transferencia peritaje → costos sigue siendo una acción humana separada y explícita del contrato anterior.

Por tanto:

`REVIEWED peritaje ≠ costos revisados ≠ buy signal`.

## Despliegue previsto

Solo después de suite completa y merge certificado:

1. aplicar `20260826010000_peritaje_evidence_workbench_v50.sql`;
2. desplegar `superbid-peritaje-evidence-workbench`;
3. desplegar `superbid-readiness-dashboard` v0.50;
4. preservar la configuración productiva de autenticación;
5. verificar 0 filas de evidencia creadas automáticamente;
6. verificar que readiness no cambie por deploy salvo cierres temporales naturales;
7. realizar UAT con evidencia real, nunca inventada.

## Criterios de aceptación

1. REVIEWED exige PDF fuente perteneciente al lote.
2. REVIEWED exige 8/8 dimensiones.
3. Cada dimensión REVIEWED exige riesgo y evidencia textual.
4. `NOT_EVALUABLE` permanece disponible.
5. REVIEWED exige low/base/high y fundamento.
6. Trigger impide divergencia entre evidencia v0.50 y revisión canónica.
7. Workbench conserva el lote durante autenticación.
8. No hay open redirects.
9. Workbench solo expone autenticación + RPC de evidencia.
10. No existe transferencia automática a costos.
11. No existe diagnóstico automático.
12. No existe buy signal.
13. Readiness enruta el peritaje exacto al workbench.
14. Contratos legacy permanecen consultables.
15. Versión de paquete = `0.50.0`.
16. Suite histórica completa PASS.
17. Producción recibe 0 revisiones ficticias durante migración/deploy.
