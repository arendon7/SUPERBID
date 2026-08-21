# v0.31 — Readiness económico explicable

## Objetivo

Explicar por qué un lote todavía no puede producir una decisión económica final y cuál es la siguiente tarea humana necesaria.

Guardrail obligatorio:

`ECONOMIC_READINESS_NOT_BUY_SIGNAL`

`READY_FOR_DECISION` significa que las evidencias y revisiones exigidas están completas. No significa `COMPRAR`.

## Fuente

`dashboard_economic_readiness_current` se construye sobre la inteligencia central del lote y las revisiones humanas específicas.

No recalcula `final_decision`, la puja máxima ni el ROI: los expone como resultados del motor económico existente.

## Bloqueos

La vista puede devolver:
- `CLOSED_OR_PAST`;
- `FASECOLDA_NOT_HIGH`;
- `COMMISSION_MISSING`;
- `PERITAJE_NOT_REVIEWED` cuando existe un peritaje público;
- `MARKET_NOT_VALIDATED`;
- `LOT_COSTS_MISSING`;
- `LOT_COSTS_INCOMPLETE`;
- `LOT_COSTS_NOT_REVIEWED`;
- `CURRENT_BID_MISSING`.

## Siguiente acción

La prioridad se expresa mediante `next_action`:
- `NO_ACTION_CLOSED`;
- `REVIEW_VALUATION`;
- `REVIEW_COMMISSION`;
- `REVIEW_PERITAJE`;
- `VALIDATE_MARKET`;
- `ENTER_LOT_COSTS`;
- `COMPLETE_LOT_COSTS`;
- `REVIEW_LOT_COSTS`;
- `WAIT_CURRENT_BID`;
- `DECISION_AVAILABLE`.

## Peritaje

Cuando existe un peritaje público, el readiness exige revisión humana `REVIEWED`. Cuando no existe peritaje público, la ausencia se conserva como `NO_PUBLIC_PERITAJE_AVAILABLE` y no se inventa evidencia.

## Costos

El readiness usa `lot_cost_overrides` específicos del lote para exigir:
- ocho campos completos;
- revisión humana vigente.

No considera los costos por defecto como sustituto de una revisión específica del lote para declarar readiness.

## API privada

Solo lectura:
- `GET /economic-readiness`;
- `GET /lots/{id}/economic-readiness`.

Filtros iniciales:
- `status`;
- `next_action`;
- `review_state`;
- `limit`.

## Alcance v0.31

Esta versión fija el contrato de datos y API. La visualización integrada en el dashboard se implementará sobre este contrato en una capa posterior, evitando duplicar lógica de negocio en HTML.
