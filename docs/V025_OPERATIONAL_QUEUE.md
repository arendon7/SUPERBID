# v0.25 — Cola operativa por cierre y presión

## Objetivo
Separar la pregunta económica (“¿es buen negocio?”) de la pregunta operativa (“¿qué lote debo revisar primero?”).

`dashboard_operational_queue` combina `dashboard_lot_current` con `lot_bid_pressure_current` sin modificar el score económico ni la decisión final.

## Campos operativos
- `pressure_level`;
- actividad observada en 2h;
- extensiones de cierre;
- `hours_to_close` existente;
- `closing_bucket`;
- `operational_rank`;
- `operational_reason`;
- `operational_interpretation`.

### Buckets de cierre
- `CLOSING_2H`;
- `CLOSING_6H`;
- `CLOSING_24H`;
- `LATER`;
- `PAST`;
- `NO_CLOSE_TIME`.

## Ranking operativo
El ranking prioriza, en este orden general:
1. `REVIEW_NOW` cerca del cierre;
2. `REVIEW_NOW` con presión HIGH;
3. otros `REVIEW_NOW`;
4. `REVIEW_SOON` cerca del cierre o con presión activa;
5. `WATCH`;
6. estados bloqueados/otros.

Los lotes pasados quedan al final.

El campo `operational_interpretation` es siempre `OPERATIONAL_TRIAGE_NOT_BUY_SIGNAL`.

## API privada
`GET /operational-queue`

Filtros admitidos:
- `state=REVIEW_NOW|REVIEW_SOON|WATCH|NO_HEADROOM|BLOCKED_VALUATION|CLOSED_OR_PAST`;
- `pressure=HIGH|MEDIUM|LOW|NONE`;
- `closing=CLOSING_2H|CLOSING_6H|CLOSING_24H|LATER|PAST|NO_CLOSE_TIME`;
- `limit=1..500`.

La respuesta se ordena por `operational_rank`, luego `review_score` y finalmente cierre.

## Guardrail
La prioridad operativa no modifica:
- `review_score`;
- `review_state`;
- `max_bid_market_validated_cop`;
- `final_decision`.

Sirve exclusivamente para administrar atención y tiempo de revisión.
