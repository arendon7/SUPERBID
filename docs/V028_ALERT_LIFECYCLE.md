# v0.28 — Alert lifecycle

v0.28 separa dos conceptos que no deben confundirse:

1. **Disposición manual**: una persona vio la alerta y la reconoció o descartó.
2. **Resolución del sistema**: la condición que originó la alerta dejó de estar vigente.

Ninguno de estos estados cambia el `review_score`, la puja máxima, los costos ni la decisión económica.

## Estados manuales

`manual_disposition` puede ser:

- `NULL`: pendiente de atención humana;
- `ACKNOWLEDGED`: reconocida;
- `DISMISSED`: descartada para efectos operativos.

La acción `REOPEN` limpia la disposición manual y vuelve a dejarla pendiente. Cada cambio se registra en `operational_alert_action_history` con estado anterior, estado nuevo, fecha y nota opcional.

La interpretación de cualquier acción humana es:

`ALERT_LIFECYCLE_ACTION_NOT_BUY_SIGNAL`

## Resolución automática

`system_resolved_at` es independiente de la disposición manual.

- `CLOSING_2H` se resuelve cuando el lote deja de cumplir `REVIEW_NOW` + cierre futuro dentro de dos horas.
- `HIGH_PRESSURE` se resuelve cuando deja de existir presión `HIGH` reciente en un lote `REVIEW_NOW` o `REVIEW_SOON`.
- `CLOSE_EXTENSION` es un evento puntual y se archiva automáticamente 24 horas después de su observación.

`system_resolution_reason` conserva la causa (`CONDITION_NO_LONGER_ACTIVE` o `EVENT_AGED_24H`).

## Feed

`dashboard_operational_alert_feed` conserva el contrato anterior de `is_open` y añade:

- `manual_disposition`;
- `system_resolved_at`;
- `system_resolution_reason`;
- `is_unattended`;
- `is_system_active`.

`is_open` significa simultáneamente pendiente de atención humana y todavía activo en el sistema.

## Dashboard

La página privada `/alerts` permite filtrar:

- Pendientes;
- Atendidas / descartadas;
- Resueltas por sistema;
- Todas.

Acciones server-rendered:

- Reconocer;
- Descartar;
- Reabrir.

La nota es opcional y está limitada a 1000 caracteres. El navegador nunca recibe `service_role`; la escritura ocurre desde el Edge Function privado mediante `dashboard_set_operational_alert_disposition(...)`.

## Automatización

El cron `superbid-alert-lifecycle-v28` ejecuta cada minuto:

1. `refresh_operational_alerts()` para detectar nuevas alertas deduplicadas;
2. `resolve_operational_alerts()` para cerrar condiciones caducadas.

El cron anterior `superbid-operational-alerts-v27` se elimina al aplicar la migración.

## Seguridad

- RLS activo en el historial de acciones;
- tabla/RPC sin permisos para `public`, `anon` ni `authenticated`;
- `service_role` es el único rol operativo;
- el read API sigue siendo estrictamente GET/read-only;
- no se almacena identidad de pujadores ni precio de reserva oculto;
- ninguna acción de lifecycle altera variables económicas o estados de adjudicación.
