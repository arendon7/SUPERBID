# v0.32 — Tablero visual de readiness económico

## Objetivo

Presentar visualmente el contrato de `dashboard_economic_readiness_current` sin duplicar ni modificar la lógica económica.

Guardrail:

`ECONOMIC_READINESS_NOT_BUY_SIGNAL`

`READY_FOR_DECISION` significa que las evidencias y revisiones requeridas permiten al motor expresar una decisión. No significa `COMPRAR`.

## Función privada

`superbid-readiness-dashboard`

Ruta:
`/functions/v1/superbid-readiness-dashboard`

Usa la misma validación privada `dashboard_token_valid`, con cookie propia `HttpOnly; Secure; SameSite=Strict`.

## Visualización

La tabla muestra:
- readiness y número de bloqueos;
- score de revisión;
- vehículo, puja y cierre;
- Fasecolda y comisión;
- estado de revisión del peritaje;
- estado de validación de mercado;
- estado/completitud de costos;
- lista de blockers;
- `next_action`;
- decisión, puja máxima y ROI del motor existente solo como contexto de lectura.

Orden:
1. menos bloqueos;
2. mayor `review_score`;
3. cierre más próximo.

## Filtros

- `status`: `BLOCKED / READY_FOR_DECISION / CLOSED`;
- `next_action`;
- `review_state`.

## Enlaces de acción

El tablero no ejecuta workflows de negocio. Enlaza a las interfaces humanas existentes:
- `REVIEW_PERITAJE` → detalle del lote, sección `#peritaje`;
- costos → detalle del lote, sección `#costs`;
- otras acciones → detalle general del lote.

## No escritura

El tablero no llama a:
- `dashboard_save_lot_costs`;
- `dashboard_save_peritaje_review`;
- `dashboard_transfer_peritaje_repair_to_costs`.

Login/logout son las únicas solicitudes POST propias de esta función.
