# v0.29 — revisión estructurada de peritajes

## Objetivo

Convertir los peritajes públicos asociados a los lotes en un flujo de revisión humana trazable antes de completar los costos específicos del vehículo.

La revisión **no es un diagnóstico automático** y no modifica automáticamente score, puja máxima, costos ni decisión final.

Guardrail obligatorio:

`MANUAL_PERITAJE_REVIEW_NOT_AUTOMATED_DIAGNOSIS`

## Estados

- `UNREVIEWED`: existe peritaje público pero no hay revisión guardada.
- `DRAFT`: existe revisión parcial o completa, pero no fue marcada como revisada.
- `REVIEWED`: las 8 dimensiones y los tres escenarios de reparación están completos y fueron confirmados explícitamente.

## Dimensiones manuales

Cada dimensión admite `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` o `NOT_EVALUABLE`:

1. mecánica;
2. transmisión;
3. carrocería;
4. seguridad;
5. eléctrico;
6. llantas;
7. documentación;
8. piezas faltantes.

`overall_risk` toma conservadoramente la dimensión de mayor riesgo. `NOT_EVALUABLE` no se convierte en riesgo bajo.

## Escenarios de reparación

La revisión registra tres valores manuales:

- `repair_low_cop`;
- `repair_base_cop`;
- `repair_high_cop`.

Se exige `low <= base <= high` y todos deben ser no negativos.

Estos valores son **estimaciones de revisión del peritaje**. No se copian a `lot_cost_overrides.repair_cop`. Para afectar el motor económico, el costo debe registrarse y revisarse explícitamente en el módulo de costos.

## Fuente

La revisión solo se permite cuando existe un `lot_attachments.kind='PERITAJE'` público para el lote. Si se indica `source_attachment_url`, la URL debe pertenecer realmente a ese lote.

## Auditoría

- `lot_peritaje_reviews`: estado actual por lote.
- `lot_peritaje_review_history`: snapshot inmutable de cada guardado.
- `dashboard_save_peritaje_review(...)`: único RPC de escritura del flujo.
- `dashboard_peritaje_review_current`: cola backend-only para `UNREVIEWED / DRAFT / REVIEWED`.

RLS está habilitado. `public`, `anon` y `authenticated` no tienen acceso directo; la aplicación usa `service_role` desde backend.

## Dashboard

Nueva navegación `Peritajes`:

`/functions/v1/superbid-dashboard/peritajes`

Filtros:
- estado de revisión de peritaje;
- estado operativo del lote.

El detalle del lote incorpora:
- PDFs públicos disponibles;
- selector de PDF fuente;
- checklist de 8 dimensiones;
- rango de reparación bajo/base/alto;
- notas;
- guardado borrador;
- marcado como revisado;
- historial de revisiones.

## API privada

- `GET /peritaje-reviews?status=&review_state=&limit=`
- `GET /lots/{id}/peritaje-review`

La read API continúa siendo GET/read-only.
