# v0.45 — Gobierno auditable de supuestos de costos

## Diagnóstico productivo

Después de desplegar v0.44, `dashboard_economic_readiness_current` seguía mostrando 292 lotes activos `BLOCKED`.

Los tres blockers de costos estaban presentes en los 292:

- `LOT_COSTS_MISSING`;
- `LOT_COSTS_INCOMPLETE`;
- `LOT_COSTS_NOT_REVIEWED`.

La causa no era solo falta de revisión:

- el único `deal_profiles` default tenía los 8 costos en `NULL`;
- `lot_cost_overrides` tenía 0 filas;
- por tanto no existía una base económica configurada para ningún lote.

Además se encontró un defecto de cobertura:

- 292 activos requerían costos;
- solo 171 aparecían en `dashboard_cost_readiness_current`;
- 121 activos quedaban fuera;
- los 121 excluidos tenían `peritaje_count = 0`.

La vista v0.30 se construyó desde `dashboard_peritaje_review_current`, por lo que convirtió accidentalmente la existencia de un peritaje público en requisito para entrar al workflow general de costos.

## Objetivo

v0.45 separa tres conceptos:

1. **Perfil de supuestos**: valores reutilizables, todavía no asociados a ningún vehículo.
2. **Aplicación al lote**: acto humano explícito que copia/snapshottea una versión REVIEWED al lote concreto.
3. **Revisión del lote**: confirmación de que esos costos son adecuados para ese vehículo; sigue siendo independiente del hecho de que el perfil esté REVIEWED.

Guardrails:

`COST_PROFILE_ASSUMPTION_NOT_LOT_COST`

`COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION`

`COST_GOVERNANCE_NOT_BUY_SIGNAL`

## Lo que v0.45 deliberadamente no hace

- no inventa valores de transferencia, SOAT/impuestos, transporte, reparación, detailing, financiación, administración o contingencia;
- no rellena `deal_profiles` automáticamente;
- no aplica un perfil a todos los lotes;
- no ofrece bulk apply;
- no modifica Fasecolda;
- no crea evidencia de mercado;
- no revisa peritajes;
- no cambia comisión ni puja actual;
- no escribe `COMPRAR` directamente;
- no considera un perfil DRAFT como utilizable.

## `cost_assumption_profile_versions`

Cada creación genera una versión inmutable.

Estados:

- `DRAFT`: puede ser parcial y nunca es aplicable;
- `REVIEWED`: exige los 8 valores completos, nota de fuente/criterio y `reviewed_at`.

Campos económicos:

- transferencia;
- impuestos / SOAT;
- transporte;
- reserva de reparación;
- detailing;
- financiación;
- administración;
- contingencia.

Cada versión conserva `profile_fingerprint` MD5 sobre los valores y la nota material.

La tabla es backend-only. `anon` y `authenticated` no tienen acceso.

## Perfil REVIEWED actual

`cost_assumption_profile_current` expone únicamente la versión REVIEWED más reciente.

Importante: esta vista no alimenta directamente el motor económico. El perfil no es un costo del lote hasta que sea aplicado explícitamente.

Esto evita que crear o cambiar un supuesto reutilizable altere silenciosamente pujas máximas de cientos de vehículos.

## RPC de creación

`dashboard_save_cost_assumption_profile(...)`

- crea una nueva versión;
- nunca actualiza una versión anterior;
- un DRAFT puede ser parcial;
- REVIEWED exige los ocho campos y nota de mínimo 10 caracteres;
- devuelve `lots_modified = 0` y `buy_signal = false`.

No ejecuta `UPDATE deal_profiles` ni toca `lot_cost_overrides`.

## Aplicación individual

`dashboard_apply_cost_profile_to_lot(...)`

Requisitos:

- lote concreto por `external_lot_id`;
- versión de perfil concreta;
- perfil obligatoriamente `REVIEWED`;
- lote no cerrado;
- modo de reparación explícito;
- confirmación independiente para marcar costos del lote como REVIEWED.

No existe una versión bulk de esta RPC.

### `PROFILE`

Usa también la reserva de reparación del perfil.

### `PRESERVE_LOT`

Mantiene el `repair_cop` ya existente en `lot_cost_overrides`.

Solo está permitido si el lote ya tiene una reparación cargada, por ejemplo mediante el flujo manual de peritaje v0.30 o una edición custom.

Esto permite reutilizar los siete costos operativos sin destruir una reparación específica del vehículo.

## Snapshot y trazabilidad

Aplicar un perfil copia valores a `lot_cost_overrides`.

Por tanto, si posteriormente se crea un perfil nuevo, un lote ya aplicado no cambia silenciosamente.

Se escribe además:

- `lot_cost_review_history`;
- `lot_cost_profile_application_history`.

La segunda tabla conserva:

- lote;
- versión y fingerprint del perfil;
- modo de reparación;
- costos previos;
- costos aplicados;
- si se marcó REVIEWED;
- nota de aplicabilidad;
- fecha.

## Corrección de cobertura

`dashboard_cost_readiness_current` mantiene su contrato de columnas pre-v0.45, pero cambia su base:

Antes:

`dashboard_peritaje_review_current`

Ahora:

`dashboard_lot_current`

Luego hace `LEFT JOIN` a peritaje y costos.

Semántica de peritaje:

- `NOT_AVAILABLE`: el lote no tiene peritaje público;
- `UNREVIEWED`: existe peritaje pero no revisión;
- `DRAFT`: revisión iniciada;
- `REVIEWED`: revisión humana completa.

Un peritaje deja de ser requisito para aparecer en costos.

## Cola v0.45

`dashboard_cost_governance_queue_v45` incluye todo lote activo `BLOCKED` que tenga cualquiera de:

- `LOT_COSTS_MISSING`;
- `LOT_COSTS_INCOMPLETE`;
- `LOT_COSTS_NOT_REVIEWED`.

La cola expone:

- blockers;
- review score;
- cierre;
- estado de peritaje;
- escenarios de reparación;
- costos actuales;
- perfil REVIEWED disponible;
- acción de gobierno sugerida.

Acciones posibles:

- `CONFIGURE_REVIEWED_PROFILE`;
- `APPLY_REVIEWED_PROFILE`;
- `TRANSFER_REPAIR_OR_APPLY_PROFILE`;
- `APPLY_PROFILE_PRESERVE_REPAIR`;
- `REVIEW_EXISTING_COSTS`;
- `COSTS_REVIEWED`.

La acción es orientación de workflow, no decisión de compra.

## Dashboard privado

Edge Function:

`superbid-cost-governance-dashboard`

Permite:

- ver el perfil REVIEWED vigente;
- crear una versión DRAFT o REVIEWED;
- revisar histórico de perfiles;
- ver todos los lotes activos con blockers de costos, tengan o no peritaje;
- abrir un lote;
- elegir `PROFILE` o `PRESERVE_LOT`;
- aplicar una versión REVIEWED solo al lote abierto;
- marcar la aplicación como DRAFT o REVIEWED;
- ir al formulario custom existente cuando el perfil no corresponda.

Autenticación:

- `dashboard_token_valid`;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- `service_role` permanece exclusivamente en servidor.

## Relación con el motor económico

v0.45 no crea un motor paralelo.

Al aplicar el perfil se escriben los mismos `lot_cost_overrides` consumidos desde v0.18/v0.21. Por tanto:

- `lot_opportunity_market_validated` sigue calculando los costos efectivos;
- `dashboard_economic_readiness_current` sigue decidiendo si faltan campos o revisión;
- `final_decision` sigue dependiendo de todas las capas de evidencia;
- un perfil REVIEWED sin aplicación a lote tiene efecto económico cero.

## Resultado esperado

Antes de v0.45:

- 121 activos sin peritaje no eran alcanzables desde la cola de costos;
- 0/292 activos tenían costos cargados;
- 0 perfiles de costos reutilizables estaban configurados.

Después de desplegar v0.45, sin introducir datos ficticios:

- la cola debe cubrir los 292 activos con blocker de costos;
- debe seguir habiendo 0 perfiles REVIEWED hasta que una persona configure valores reales;
- no debe aparecer ningún costo ni decisión nueva por el mero despliegue;
- la infraestructura queda lista para convertir supuestos reales revisados en snapshots explícitos por vehículo.
