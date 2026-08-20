# v0.17 — Motor preliminar de oportunidad

## Objetivo

Convertir la ficha técnica/financiera del lote en un techo económico preliminar sin afirmar todavía que un vehículo debe comprarse.

La decisión final queda bloqueada hasta contar con:

1. costos fijos configurados;
2. comparables reales de mercado;
3. revisión del peritaje/riesgo cuando aplique.

## Variables conocidas automáticamente

Por lote:

- puja actual;
- número de pujas;
- fecha/hora de cierre;
- comisión pública de Superbid;
- IVA general aplicado a la comisión;
- Fasecolda actual si el match es `HIGH`;
- histórico Fasecolda;
- peritaje disponible/no disponible.

## Perfil preliminar

`PRELIMINARY_FASECOLDA`

Parámetros iniciales de política:

- IVA sobre comisión: `19%`;
- utilidad objetivo: `12%` del valor de reventa;
- utilidad mínima: `COP 3.000.000`;
- factor conservador sobre Fasecolda: `90%`.

Los siguientes costos permanecen `NULL` hasta que sean configurados:

- traspaso;
- impuestos/SOAT;
- transporte;
- reparación;
- detailing/alistamiento;
- financiación/costo de capital;
- tasa administrativa;
- contingencia.

Esto es deliberado: el sistema no inventa costos desconocidos.

## Fórmulas

### Reventa preliminar

`PreliminaryResale = Fasecolda × 0.90`

Solo se calcula para match Fasecolda `HIGH`.

### Multiplicador de puja

Si la comisión pública es `c` y el IVA es `v`:

`BidMultiplier = 1 + c × (1 + v)`

Ejemplo: comisión 6,5% + IVA 19%:

`1 + 0.065 × 1.19 = 1.07735`

### Utilidad objetivo

`TargetProfit = max(COP 3.000.000, PreliminaryResale × 12%)`

### Techo antes de costos fijos

`CeilingBeforeFixedCosts = (PreliminaryResale - TargetProfit) / BidMultiplier`

Este dato sirve para priorizar análisis, **no para ofertar**.

### Puja máxima preliminar

Solo existe cuando todos los costos fijos están configurados:

`MaxBidPreliminary = (PreliminaryResale - FixedCosts - TargetProfit) / BidMultiplier`

## Estados

- `REVIEW_VALUATION`: Fasecolda no es `HIGH`.
- `REVIEW_COMMISSION`: falta comisión pública.
- `NO_CURRENT_BID`: falta puja actual.
- `CONFIGURE_COSTS`: valoración y comisión existen, pero faltan costos fijos.
- `MARKET_VALIDATION_PENDING`: costos completos, pero aún no hay comparables de mercado.
- `PRELIMINARY_OVER_CEILING`: la puja supera el techo preliminar.
- `PRELIMINARY_WITHIN_CEILING`: la puja está por debajo del techo preliminar, pero la recomendación sigue siendo preliminar.

En todos los casos de v0.17:

`final_buy_recommendation_available = false`

## Vista central

`lot_opportunity_preliminary`

Incluye, entre otros:

- `current_bid_cop`
- `commission_percent_public`
- `fasecolda_current_cop`
- `fasecolda_12m_ago_cop`
- `preliminary_resale_cop`
- `target_profit_cop`
- `ceiling_before_fixed_costs_cop`
- `max_bid_preliminary_cop`
- `discount_vs_fasecolda_pct`
- `preliminary_headroom_before_fixed_costs_cop`
- `peritaje_count`
- `market_comparable_count`
- `opportunity_state`

## Uso correcto

v0.17 sirve para ordenar dónde mirar primero. No sustituye:

- inspección mecánica;
- lectura de peritaje;
- condiciones particulares de la subasta;
- costos de logística/traspaso;
- validación de mercado de reventa.
