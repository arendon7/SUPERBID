# v0.24 — Presión competitiva observada

## Objetivo
Convertir los cambios observados entre snapshots en una señal descriptiva de intensidad competitiva por lote, sin incorporarla todavía al score económico ni a la decisión final.

## Métricas
`lot_bid_pressure_current` calcula:
- cambios observados acumulados;
- incremento acumulado de precio;
- incremento acumulado del contador de pujas;
- cambios, pujas e incremento de precio en 2h y 6h;
- cambios y pujas en 24h;
- último cambio observado;
- número de snapshots y horas de observación;
- extensiones de cierre detectadas cuando `closes_at` aumenta entre snapshots.

## Nivel descriptivo
- `HIGH`: 2+ cambios en 2h, 4+ pujas observadas en 2h o 2+ extensiones;
- `MEDIUM`: actividad en 6h, 3+ cambios acumulados, 5+ pujas acumuladas o una extensión;
- `LOW`: existe al menos un cambio observado;
- `NONE`: sin cambios observados.

Los umbrales son heurísticos y están etiquetados como `OBSERVATIONAL_ONLY_NOT_BUY_SIGNAL`.

## Interpretación
La presión competitiva describe actividad. No implica que un lote sea atractivo, barato ni rentable. Un lote con presión alta puede tener valoración bloqueada, headroom insuficiente o costos desconocidos.

La señal no modifica por sí sola:
- `review_score`;
- `review_state`;
- `max_bid_market_validated_cop`;
- `final_decision`.

## API privada
`GET /lots/{id}/bid-pressure`

## Dashboard
El detalle del lote muestra:
- nivel de presión;
- cambios últimas 2h;
- pujas observadas +2h;
- incremento de precio +2h;
- cambios y pujas acumuladas;
- incremento acumulado;
- extensiones de cierre;
- último cambio.

## Seguridad
Vista y RPC son backend-only (`service_role`). No se almacena identidad de pujadores, `reservedPrice` ni una secuencia inventada de lances individuales.
