# v0.22 — Inteligencia histórica central

## Objetivo
Cumplir el requisito de consultar y descargar valores históricos sin mezclar semánticas distintas de subasta.

## Tipos de valor histórico
`dashboard_history_export` conserva tres estados:

- `SALE_CONFIRMED`: existe `sale_price_confirmed_cop` con evidencia explícita de venta/adjudicación;
- `CLOSING_OBSERVED`: existe un precio de cierre observado pero no confirmación de venta;
- `NO_FINAL_VALUE`: no existe valor final defendible.

`NO_FINAL_VALUE` **no se rellena con la última puja**.

## Timeline por lote
`dashboard_lot_timeline(external_lot_id)` entrega:

- outcome y confianza;
- snapshots observados de precio, número de pujas, estado y cierre;
- histórico individual de lances solo cuando Superbid lo haya expuesto públicamente;
- histórico mensual Fasecolda para el código `HIGH` seleccionado;
- proveniencia de los datos;
- historial auditable de revisiones de costos.

La respuesta deliberadamente no devuelve el `evidence` crudo de snapshots para evitar exponer accidentalmente campos que no deban formar parte de la inteligencia de puja.

## Dashboard
Nueva navegación:
- Oportunidades;
- Histórico;
- CSV histórico.

El detalle del lote muestra:
- venta confirmada y cierre observado en campos separados;
- trayectoria de snapshots;
- lances individuales, si existen;
- serie Fasecolda;
- proveniencia;
- revisiones históricas de costos.

Cuando no existen lances individuales se indica expresamente: **no se infieren desde snapshots**.

## Exportación
`superbid_historico.csv` incluye campos separados para:
- oferta inicial;
- cierre observado;
- venta confirmada;
- valor histórico;
- tipo de valor histórico;
- confianza/fuente;
- snapshots;
- peritajes;
- Fasecolda;
- URL del lote.

El archivo usa UTF-8 con BOM para abrir correctamente en Excel.

## Seguridad
- vista y RPC solo `service_role`;
- dashboard y read API mantienen autenticación privada;
- `anon/authenticated` no pueden leer la vista ni ejecutar la función;
- no se expone identidad de pujadores ni precio de reserva.
