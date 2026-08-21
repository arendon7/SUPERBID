# v0.21 — Revisión de costos por lote

## Objetivo
Convertir el análisis del peritaje en datos económicos auditables por vehículo.

## Costos capturados
- traspaso;
- impuestos / SOAT;
- transporte;
- reparación;
- alistamiento / detailing;
- financiación;
- administración;
- contingencia.

## Flujo
Desde el detalle del lote en `superbid-dashboard` se puede:
1. abrir el peritaje público;
2. registrar costos en COP;
3. guardar un borrador incompleto;
4. añadir fuente/notas de revisión;
5. marcar el costo como revisado únicamente cuando los 8 campos estén completos.

## Regla de revisión
Cualquier guardado reemplaza `reviewed_at`:
- borrador o edición -> `reviewed_at = NULL`;
- `Guardar y marcar revisado` + 8 costos completos -> nuevo timestamp de revisión.

Esto evita que una cifra modificada conserve una aprobación anterior.

## Auditoría
Cada guardado crea una fila en `lot_cost_review_history` con el snapshot completo, nota y si fue marcado revisado.

## Seguridad
- `lot_cost_review_history` tiene RLS activo;
- `anon` y `authenticated` no tienen acceso;
- `dashboard_save_lot_costs(...)` solo puede ejecutarlo `service_role`;
- el navegador no conoce `service_role`;
- el formulario solo funciona después de validar la cookie privada del dashboard;
- valores negativos o superiores a COP 50.000 millones se rechazan.

## Efecto económico
Los costos revisados alimentan `lot_opportunity_market_validated`.

Aun con costos completos, `COMPRAR/VIGILAR/NO_PUJAR` solo se habilita si la validación de mercado también está disponible. Mientras Mercado Libre siga `APP_REQUIRED`, la decisión permanece `MARKET_VALIDATION_PENDING`.
