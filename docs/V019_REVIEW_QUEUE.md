# v0.19 — Cola de revisión priorizada

## Objetivo
Priorizar qué vehículos y peritajes revisar primero mientras la validación de mercado y los costos definitivos siguen pendientes.

`REVIEW_NOW` **no significa comprar**. Es una prioridad de análisis humano.

## Fuente
La vista `lot_review_queue_current` parte de `lot_opportunity_preliminary`, por lo que utiliza únicamente información ya disponible y trazable:

- puja actual;
- cierre;
- número de pujas;
- comisión pública;
- Fasecolda cuando el match es `HIGH`;
- techo preliminar antes de costos fijos;
- peritaje disponible.

No usa un precio de venta de Mercado Libre mientras OAuth no esté `READY`, y no sustituye el cálculo final de v0.18.

## Score de revisión
Máximo 100 puntos:

- headroom preliminar relativo a Fasecolda: hasta 40;
- peritaje público disponible: 25;
- cierre próximo: hasta 20;
- actividad de pujas: hasta 10;
- comisión pública favorable: hasta 5.

### Cierre
- <=24h: 20 puntos;
- <=72h: 12;
- <=168h: 5;
- después del cierre: 0.

### Actividad
- >=5 pujas: 10;
- >=1 puja: 5;
- 0: 0.

## Estados
- `CLOSED_OR_PAST`
- `BLOCKED_VALUATION`
- `NO_HEADROOM`
- `REVIEW_NOW` — score >=65;
- `REVIEW_SOON` — score >=45;
- `WATCH`.

## Guardas
Un lote no puede entrar a la priorización económica útil si Fasecolda no está `HIGH` o el headroom preliminar es <=0.

El peritaje aumenta prioridad porque permite evaluar riesgo más rápido, pero **no se interpreta como garantía de buen estado mecánico**.

`review_reasons` conserva el desglose de puntos y marca siempre:
- `needs_market_validation=true`;
- `needs_cost_review=true`.

Por tanto, esta vista jamás genera `COMPRAR`, `VIGILAR` ni `NO_PUJAR`; esos estados pertenecen a `lot_opportunity_market_validated` después de mercado + costos.

## Uso recomendado
Ordenar por:
1. `review_state`;
2. `review_score` desc;
3. `closes_at` asc.

La cola sirve para decidir dónde invertir primero el tiempo de lectura del peritaje, estimación de reparación y validación de mercado.
