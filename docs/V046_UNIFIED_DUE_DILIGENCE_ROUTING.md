# v0.46 — Unified Due Diligence Routing

## Problema observado en producción

Después de v0.44 y v0.45, SUPERBID ya tenía workflows especializados para resolver evidencia de mercado y gobierno de costos, pero el tablero de readiness seguía usando el contrato anterior.

Snapshot productivo al iniciar v0.46:

- 403 lotes en readiness;
- 292 `BLOCKED`;
- 111 `CLOSED`;
- 0 `READY_FOR_DECISION`;
- 292 con `MARKET_NOT_VALIDATED`;
- 292 con los tres blockers de costos;
- 198 con `FASECOLDA_NOT_HIGH`;
- 172 con `PERITAJE_NOT_REVIEWED`;
- 26 con `COMMISSION_MISSING`;
- 10 con `CURRENT_BID_MISSING`.

Había además 20 lotes con exactamente cuatro blockers:

- `MARKET_NOT_VALIDATED`;
- `LOT_COSTS_MISSING`;
- `LOT_COSTS_INCOMPLETE`;
- `LOT_COSTS_NOT_REVIEWED`.

En esos casos Fasecolda ya era HIGH, la comisión estaba presente y existía puja actual. Son los casos de menor fricción documental, pero **no son automáticamente mejores negocios**.

## Defecto de UX/operación

`superbid-readiness-dashboard` seguía consultando directamente `dashboard_economic_readiness_current` y ordenaba principalmente por número de blockers.

Al mismo tiempo, la base ya tenía `dashboard_due_diligence_queue`, que combina:

- readiness económico;
- cierre de subasta;
- presión observada;
- prioridad operacional;
- `due_diligence_rank`;
- `due_diligence_stage`.

Además las rutas del tablero estaban desactualizadas:

- `VALIDATE_MARKET` no abría `superbid-market-review-dashboard`;
- los blockers de costos seguían llevando al formulario legacy `#costs`, no a `superbid-cost-governance-dashboard`;
- el operador no tenía accesos contextuales a todos los workflows que podían resolver blockers secundarios.

## Objetivo v0.46

Convertir Readiness en un **Due Diligence Command Center** que haga dos cosas y nada más:

1. priorizar el trabajo humano usando la señal operacional ya calculada por SUPERBID;
2. enrutar al workflow especializado que puede registrar evidencia para cada blocker.

Guardrail principal:

`DUE_DILIGENCE_ROUTING_NOT_BUY_SIGNAL`

Se preserva además:

`ECONOMIC_READINESS_NOT_BUY_SIGNAL`

## Arquitectura

v0.46 es deliberadamente read-only respecto de datos de negocio.

No crea:

- tablas de negocio;
- RPCs de escritura;
- overrides;
- evidencia de mercado;
- costos;
- matches Fasecolda;
- decisiones.

Sí incluye una migración **exclusivamente de contrato de lectura**:

`20260825200000_due_diligence_fasecolda_provenance_v46.sql`

Esta migración hace `create or replace view` sobre `dashboard_due_diligence_queue` para anexar al final del contrato tres campos de proveniencia que ya existen en readiness:

- `fasecolda_match_origin`;
- `fasecolda_automatic_status`;
- `fasecolda_match_interpretation`.

Los primeros 40 campos, el ranking, los blockers, el readiness y la autoridad económica permanecen intactos. La vista sigue revocada para `public`, `anon` y `authenticated`, y disponible únicamente para `service_role`.

El dashboard consulta:

`dashboard_due_diligence_queue`

Orden canónico:

1. `due_diligence_rank ASC`;
2. `blocker_count ASC`;
3. `review_score DESC`;
4. `closes_at ASC`.

Así se conserva primero la urgencia operacional y, dentro de ella, se favorecen casos que requieren menos trabajo documental.

## Etapas visibles

La UI puede filtrar las etapas existentes del contrato de due diligence, entre otras:

- `UNBLOCK_NOW`;
- `UNBLOCK_SOON`;
- `UNBLOCK_TODAY`;
- `PRIORITY_REVIEW`;
- `PREPARE_REVIEW`;
- `BACKLOG`;
- etapas de decisión si en el futuro existen lotes `READY_FOR_DECISION`.

También expone presión y `closing_bucket` sin convertirlos en recomendación económica.

## Enrutamiento de la siguiente acción

### `REVIEW_VALUATION`

Abre `superbid-fasecolda-workbench`.

### `REVIEW_PERITAJE`

Abre el detalle del lote en la sección `#peritaje`.

### `VALIDATE_MARKET`

Abre directamente `superbid-market-review-dashboard/lots/<external_lot_id>`.

### Costos

`ENTER_LOT_COSTS`, `COMPLETE_LOT_COSTS` y `REVIEW_LOT_COSTS` abren `superbid-cost-governance-dashboard/lots/<external_lot_id>`.

### Comisión, puja y decisión disponible

`REVIEW_COMMISSION`, `WAIT_CURRENT_BID` y `DECISION_AVAILABLE` abren el detalle canónico del lote. v0.46 no inventa una comisión ni una puja.

## Shortcuts por blocker

Además del workflow principal, cada fila muestra accesos contextuales derivados de sus blockers actuales:

- Fasecolda;
- Peritaje;
- Mercado;
- Costos;
- Lote para comisión/puja.

Los shortcuts son navegación pura. No ejecutan mutaciones.

## Fast lane

La marca `FAST LANE` solo aparece si el lote está `BLOCKED` y sus blockers son **exactamente**:

- `MARKET_NOT_VALIDATED`;
- `LOT_COSTS_MISSING`;
- `LOT_COSTS_INCOMPLETE`;
- `LOT_COSTS_NOT_REVIEWED`.

No depende de marca, precio, ROI, descuento o score económico.

Interpretación correcta:

> Menor fricción documental para alcanzar una evaluación económica completa.

Interpretaciones prohibidas:

- oportunidad recomendada;
- comprar;
- mayor ROI;
- vehículo barato;
- puja autorizada.

## Seguridad

El dashboard mantiene el patrón privado existente:

- validación server-side con `dashboard_token_valid`;
- `SUPABASE_SERVICE_ROLE_KEY` solo en Edge Runtime;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- navegador sin acceso al service role.

v0.46 no agrega superficie de escritura de negocio.

## Navegación

La cabecera del command center expone explícitamente Dashboard, Due diligence, Fasecolda, Mercado, Costos, Peritajes y Alertas.

## Compatibilidad histórica

v0.46 parte del `main` que ya contiene el patch v0.45.1 y su índice de FK sobre `lot_cost_profile_application_history(profile_version_id)`. Ese patch se conserva intacto. Sus tests históricos y el contrato visual v0.33 se mantienen forward-compatible: la proveniencia Fasecolda continúa visible, pero `REVIEW_VALUATION` se enruta al workbench unificado actual en lugar del resolver v0.33 directo.

## Criterios de aceptación

1. El dashboard consulta `dashboard_due_diligence_queue`, no una copia local de la prioridad.
2. La prioridad respeta `due_diligence_rank` antes del blocker count.
3. `VALIDATE_MARKET` abre exactamente el workflow v0.44 del lote.
4. Las acciones de costos abren exactamente el workflow v0.45 del lote.
5. Fasecolda y peritaje conservan sus workflows propios.
6. Los shortcuts se derivan de blockers reales.
7. `FAST LANE` requiere exactamente los cuatro blockers permitidos.
8. No existe ningún RPC de negocio ni write de negocio en v0.46.
9. La migración v0.46 modifica únicamente el contrato read-only de `dashboard_due_diligence_queue` y preserva sus 40 campos previos en el mismo orden.
10. La autenticación privada permanece intacta.
11. v0.45.1 permanece funcional y versionable hacia adelante.
12. La versión del paquete es `0.46.0`.

## Gate de merge y despliegue

Antes del merge debe cumplirse:

- CI completo verde sobre el merge sintético del HEAD final;
- rama `behind_by=0` respecto de `main`;
- prevalidación productiva read-only del contrato actual y de los conteos relevantes;
- validación transaccional de la migración cuando sea posible, sin dejar cambios productivos.

Después del merge:

1. aplicar `20260825200000_due_diligence_fasecolda_provenance_v46.sql`;
2. verificar contrato, permisos y conteos post-migración;
3. desplegar únicamente `superbid-readiness-dashboard`, fijado al SHA inmutable del merge;
4. confirmar que readiness, blockers y decisiones no fueron alterados por el despliegue.
