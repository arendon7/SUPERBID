# v0.26 — Dashboard de prioridad operativa

## Objetivo

Convertir `dashboard_operational_queue` en la fuente de la portada del dashboard privado para responder una pregunta operativa distinta de la valoración económica:

> ¿Qué lote merece atención primero?

La prioridad operativa **no reemplaza** `review_score`, `review_state`, la puja máxima ni la decisión final.

## Fuente

La portada consulta `dashboard_operational_queue`, que hereda la ficha económica de `dashboard_lot_current` y añade:

- `pressure_level`;
- actividad observada en 2h;
- extensiones de cierre;
- `closing_bucket`;
- `operational_rank`;
- `operational_reason`;
- `operational_interpretation=OPERATIONAL_TRIAGE_NOT_BUY_SIGNAL`.

## Filtros visuales

El dashboard es server-rendered y usa formularios GET, sin JavaScript cliente.

Filtros:

- estado de revisión: `REVIEW_NOW`, `REVIEW_SOON`, `WATCH` o todos;
- presión: `HIGH`, `MEDIUM`, `LOW`, `NONE` o todas;
- cierre: `<2h`, `<6h`, `<24h`, posterior o cualquiera.

## Orden

1. `operational_rank ASC`;
2. `review_score DESC`;
3. `closes_at ASC`.

La tabla muestra de manera independiente:

- prioridad operativa y razón;
- score de revisión;
- vehículo;
- puja actual;
- cierre y horas restantes;
- ventana de cierre;
- presión y actividad observada de 2h;
- Fasecolda;
- headroom preliminar;
- pujas;
- peritaje;
- estado de mercado;
- estado de revisión.

## Guardrails

La portada no escribe ni recalcula:

- `max_bid_market_validated_cop`;
- `final_decision`;
- costos específicos;
- `review_score`;
- `review_state`.

Los filtros solo cambian qué filas se presentan y en qué orden operativo.

## Compatibilidad

Se conservan:

- autenticación por cookie `HttpOnly; Secure; SameSite=Strict`;
- histórico y CSV;
- detalle por lote;
- peritajes;
- snapshots y eventos observados;
- presión competitiva;
- formulario auditable de costos.
