# v0.48 — Completion-Safe Market & Cost Flow

## Diagnóstico productivo

Después de v0.47, SUPERBID conserva correctamente el lote a través del flujo Fasecolda. La siguiente auditoría se concentró en el camino más corto hacia una evaluación económica completa.

Snapshot operacional al iniciar v0.48:

- 403 lotes en readiness;
- 264 `BLOCKED`;
- 139 `CLOSED`;
- 0 `READY_FOR_DECISION`;
- 24 lotes bloqueados únicamente por:
  - `MARKET_NOT_VALIDATED`;
  - `LOT_COSTS_MISSING`;
  - `LOT_COSTS_INCOMPLETE`;
  - `LOT_COSTS_NOT_REVIEWED`.

Esos 24 casos constituyen el menor recorrido documental restante, pero **no son una recomendación de compra**.

Además, `cost_assumption_profile_current` no tenía ningún perfil `REVIEWED` al momento de la auditoría. Ese dato es un snapshot productivo y no un invariante del software.

## Defecto encontrado

Las vistas v0.44 y v0.45 son deliberadamente colas de pendientes:

- `dashboard_market_review_queue_v44` solo contiene lotes que todavía tienen `MARKET_NOT_VALIDATED`;
- `dashboard_cost_governance_queue_v45` solo contiene lotes que todavía tienen blockers de costos.

Ese diseño es correcto para priorización, pero generaba un problema en las páginas de detalle.

### Mercado

El detalle obtenía el lote desde la propia cola pendiente. Después de guardar un set manual como `REVIEWED`, el blocker podía desaparecer y la aplicación redirigía nuevamente al detalle del mismo lote. Como el lote ya no estaba en la cola, la siguiente petición podía terminar en 404.

### Costos

Después de aplicar un perfil al lote, el flujo regresaba a la lista global. Si la aplicación `REVIEWED` resolvía los blockers, el caso desaparecía de la cola y se perdía continuidad. Además:

- el login no preservaba el lote;
- si no existía perfil `REVIEWED`, crear uno desde el contexto de un vehículo no tenía una ruta explícita de regreso al mismo caso.

## Objetivo

Hacer que Mercado y Costos sean seguros al completar una etapa:

`Due Diligence → workflow → escritura humana → estado canónico del mismo lote`

Reglas:

1. una escritura `DRAFT` mantiene al operador en el workflow actual;
2. una escritura `REVIEWED` que puede resolver el blocker lleva al readiness canónico del mismo lote;
3. si el lote ya no pertenece a la cola pendiente, la UI no produce 404 ni asume éxito: muestra un estado neutro y enlaza al readiness;
4. autenticación conserva únicamente un `external_lot_id` numérico validado;
5. crear un perfil reusable nunca lo aplica automáticamente a un lote.

Guardrail adicional:

`COMPLETION_ROUTING_NOT_BUY_SIGNAL`

## Mercado

### Autenticación y contexto

`superbid-market-review-dashboard` reconoce el lote solo desde una ruta interna con el patrón:

`/lots/<5–12 dígitos>`

Si el operador debe autenticarse, el login transporta únicamente ese ID validado como campo oculto y reconstruye server-side el destino interno.

No se acepta:

- `return_to`;
- `redirect_uri`;
- `redirect_url`;
- URL arbitraria de retorno.

### Guardado DRAFT

`dashboard_save_manual_market_evidence` sigue siendo el único RPC de negocio del workflow.

Si `p_mark_reviewed=false`:

- se guarda el DRAFT según el contrato v0.44;
- el operador vuelve al detalle exacto del mismo lote;
- el blocker continúa pendiente.

### Guardado REVIEWED

Si `p_mark_reviewed=true`, siguen vigentes todos los controles v0.44:

- mínimo 3 comparables;
- URLs HTTPS;
- URLs únicas dentro del set;
- mismo año del lote;
- precio dentro de rango;
- nota de fuente requerida;
- cálculo backend de P25, quick sale, dispersión y confianza.

Después del RPC, la UI redirige a:

`superbid-readiness-dashboard?lot=<id>`

No vuelve a consultar obligatoriamente la cola de pendientes, porque el blocker puede haber desaparecido legítimamente.

### Lote ausente de la cola

Un lote ausente ya no genera una conclusión implícita ni un 404 de negocio. La UI informa únicamente que el lote dejó de pertenecer a la cola pendiente y ordena consultar el readiness canónico.

Esto cubre tanto:

- blocker resuelto;
- cambio de estado por otra causa;
- cierre temporal de subasta;
- cualquier transición legítima del backend.

## Costos

### Perfil reusable

Se conserva la separación v0.45:

`COST_PROFILE_ASSUMPTION_NOT_LOT_COST`

Crear una versión de perfil:

- no modifica lotes;
- no ejecuta `dashboard_apply_cost_profile_to_lot`;
- requiere los 8 valores y nota para quedar `REVIEWED`;
- puede quedar `DRAFT`;
- registra su propia evidencia y fingerprint.

Cuando el operador llega desde un lote sin perfil `REVIEWED`, la UI ofrece configurar el perfil en contexto. El único valor transportado es `return_lot`, validado como 5–12 dígitos. Después de guardar el perfil, la aplicación vuelve al mismo lote.

**Volver al lote no significa aplicarle el perfil.** El operador todavía debe ejecutar una segunda acción explícita e individual.

### Aplicación individual

Se conserva:

`COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION`

El RPC sigue siendo:

`dashboard_apply_cost_profile_to_lot`

No existe bulk apply.

El operador selecciona:

- perfil `REVIEWED`;
- modo de reparación `PROFILE` o `PRESERVE_LOT` cuando corresponda;
- nota de aplicabilidad;
- si desea marcar los costos del lote como `REVIEWED`.

### Aplicación DRAFT

Si el lote no se marca `REVIEWED`:

- permanece en el detalle de Costos;
- se muestra confirmación de DRAFT;
- el workflow continúa pendiente.

### Aplicación REVIEWED

Si se marca `REVIEWED`:

- la aplicación sigue siendo individual;
- después del RPC se abre `readiness?lot=<id>`;
- el siguiente blocker real lo decide el motor canónico, no la UI de Costos.

### Lote ausente de la cola

Al igual que Mercado, un lote que ya no está en `dashboard_cost_governance_queue_v45` recibe una pantalla neutral con acceso a readiness, no un 404 de negocio.

## Autoridad de escritura

v0.48 no añade migraciones, tablas, vistas, triggers ni RPC.

Mercado conserva exactamente:

- `dashboard_token_valid`;
- `dashboard_save_manual_market_evidence`.

Costos conserva exactamente:

- `dashboard_token_valid`;
- `dashboard_save_cost_assumption_profile`;
- `dashboard_apply_cost_profile_to_lot`.

No se añade ninguna escritura a:

- Fasecolda;
- peritajes;
- puja actual;
- comisión;
- ROI;
- puja máxima;
- decisión final.

## Autenticación

Ambos dashboards mantienen:

- validación server-side con `dashboard_token_valid`;
- service role únicamente en Edge Runtime;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- rutas internas construidas por el servidor.

## Datos humanos que v0.48 no inventa

v0.48 deliberadamente no crea datos de negocio para demostrar el flujo.

### Mercado

Se requieren comparables reales proporcionados o revisados por una persona autorizada.

### Costos

Se requieren supuestos reales para:

1. transferencia;
2. impuestos / SOAT;
3. transporte;
4. reparación;
5. detailing;
6. financiación;
7. administración;
8. contingencia.

Hasta que exista un perfil `REVIEWED` con evidencia suficiente, SUPERBID debe seguir mostrando el blocker.

## Criterios de aceptación

1. Login de Mercado conserva un lote válido.
2. Login de Costos conserva un lote válido.
3. No existe redirect arbitrario controlado por navegador.
4. Mercado DRAFT permanece en el lote.
5. Mercado REVIEWED va al readiness del mismo lote.
6. Un lote que salió de la cola de Mercado no produce un 404 de negocio.
7. Crear perfil de costos puede volver al mismo lote.
8. Crear perfil nunca llama al RPC de aplicación.
9. Aplicación DRAFT permanece en Costos.
10. Aplicación REVIEWED va al readiness del mismo lote.
11. Un lote que salió de la cola de Costos no produce un 404 de negocio.
12. No existe bulk apply.
13. La autoridad de RPC no aumenta.
14. Los guardrails v0.44/v0.45 siguen visibles.
15. No existe migración v0.48.
16. Package version = `0.48.0`.
17. Suite histórica completa verde.

## Despliegue

Después de merge certificado, desplegar únicamente desde el SHA inmutable del merge:

- `superbid-market-review-dashboard`;
- `superbid-cost-governance-dashboard`.

No aplicar migraciones.

Post-deploy:

- comprobar `ACTIVE` y configuración de autenticación;
- verificar que el despliegue no generó evidencia ni perfiles por sí mismo;
- verificar readiness y conteos de negocio;
- mantener separado el UAT humano que requiere comparables y supuestos de costos reales.
