# v0.23 — Cambios observados de puja/precio

## Problema
El contrato público colombiano de `/seo/offers/` expone agregados como `totalBids`, `totalBidders`, `price`, incrementos y `winnerBid`, pero no expone una lista verificable de lances individuales.

Por tanto, el sistema **no reconstruye lances individuales** a partir de snapshots.

## Fuente
`lot_observed_bid_events` compara snapshots consecutivos del mismo lote mediante `lag()` y conserva únicamente el primer snapshot y los intervalos donde cambió el precio mostrado o el contador de pujas.

Campos:
- fecha/hora observada;
- precio anterior y actual;
- delta de precio;
- contador de pujas anterior y actual;
- delta del contador;
- estado y cierre vigentes;
- tipo de cambio observado;
- `is_individual_bid=false` siempre.

Tipos:
- `INITIAL_OBSERVATION`
- `PRICE_AND_BID_COUNT_CHANGE`
- `PRICE_CHANGE_OBSERVED`
- `BID_COUNT_CHANGE_OBSERVED`

## Interpretación
Un intervalo puede contener más de una puja. Por ejemplo, si el contador pasa de 3 a 5 y el precio sube COP 1 M, sabemos que entre dos observaciones aparecieron **dos pujas adicionales**, pero no conocemos los dos importes ni sus tiempos individuales.

Esto se presenta como **evento observado**, nunca como historial individual de lances.

## API
`GET /lots/{id}/observed-bid-events`

## Dashboard
El detalle del lote presenta una tabla independiente:

**Cambios observados de puja/precio — NO son lances individuales**

El histórico individual de lances sigue siendo una sección separada y solo se llena si una fuente pública realmente enumera esos lances.

## Seguridad
- vista y RPC solo `service_role`;
- sin identidad de pujadores;
- sin `reservedPrice`;
- no se expone `evidence` crudo del snapshot.
