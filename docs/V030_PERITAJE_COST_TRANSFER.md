# v0.30 — Transferencia explícita de reparación a costos

## Objetivo

Conectar una revisión manual de peritaje ya confirmada con el costo económico de reparación sin crear automatismos que alteren la decisión de compra.

## Regla central

`MANUAL_PERITAJE_COST_TRANSFER_NOT_AUTOMATIC`

El sistema nunca copia por sí solo los escenarios `LOW / BASE / HIGH` del peritaje a `lot_cost_overrides.repair_cop`.

## Preconditions

La transferencia requiere:
1. lote existente;
2. peritaje público asociado;
3. revisión de peritaje marcada `REVIEWED`;
4. los tres escenarios de reparación disponibles;
5. selección humana de `LOW`, `BASE` o `HIGH`;
6. confirmación explícita en el dashboard.

## Efecto de la transferencia

Solo `repair_cop` se reemplaza por el escenario elegido. Los demás costos existentes se conservan.

La operación siempre deja `lot_cost_overrides.reviewed_at = NULL`. Por tanto, una revisión económica previa queda invalidada y debe volver a ser confirmada después de completar/verificar los ocho costos.

Cada transferencia genera:
- un snapshot en `lot_cost_review_history` con `marked_reviewed=false`;
- una fila en `peritaje_repair_cost_transfer_history` con escenario, valor seleccionado, valor anterior, fuente y nota.

## Cola de preparación de costos

`dashboard_cost_readiness_current` muestra:
- estado del peritaje: `UNREVIEWED / DRAFT / REVIEWED`;
- estado económico: `NO_COSTS / DRAFT / REVIEWED`;
- número de campos de costo completados `0..8`;
- proveniencia del costo de reparación: `NOT_TRANSFERRED / MATCH_LOW / MATCH_BASE / MATCH_HIGH / CUSTOM`;
- si el peritaje está habilitado para transferencia.

## Dashboard

Nueva página privada:
`/functions/v1/superbid-dashboard/costos`

En el detalle del lote, la transferencia requiere seleccionar el escenario y marcar un checkbox de confirmación explícita antes del POST.

## API privada

Solo lectura:
- `GET /cost-readiness`;
- `GET /lots/{id}/cost-readiness`.

## Límites deliberados

La transferencia no:
- marca costos como revisados;
- cambia directamente `review_score` o `review_state`;
- modifica una puja máxima por sí sola;
- cambia `final_decision`;
- interpreta el peritaje como diagnóstico automático.

Los cálculos económicos pueden reaccionar posteriormente a los costos únicamente conforme a las reglas ya existentes de revisión y validación de mercado.
