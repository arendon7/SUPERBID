# v0.49 — Condition Evidence Gate

## Problema encontrado

La auditoría posterior a v0.48 detectó una asimetría importante en `dashboard_economic_readiness_current`.

Hasta v0.48:

- si existía peritaje público, el lote quedaba bloqueado hasta que ese peritaje fuera revisado;
- si **no** existía peritaje público, el sistema solo mostraba `NO_PUBLIC_PERITAJE_AVAILABLE` como warning;
- por tanto, un lote sin ninguna evidencia pública de condición podía llegar a `READY_FOR_DECISION` después de resolver Fasecolda, comisión, mercado, costos y puja.

Esto no era una escritura incorrecta ni una señal automática de compra, pero sí una definición insuficiente de readiness: ausencia de evidencia física podía ser interpretada como ausencia de blocker.

En producción, los 24 casos que v0.48 identificó como el camino documental más corto tenían precisamente:

- Fasecolda `HIGH`;
- peritaje `NOT_AVAILABLE`;
- mercado sin validar;
- costos `NO_COSTS`;
- 0/8 campos de costos.

Por eso v0.49 corrige el contrato antes de automatizar Mercado o costos.

## Regla central

Desde v0.49:

> **No public peritaje ≠ condition cleared.**

La falta de peritaje público es un gate explícito de condición.

El sistema no intenta diagnosticar el vehículo a partir de la ausencia de documento. Exige una disposición humana auditable sobre cómo tratar esa incertidumbre.

Guardrails:

- `CONDITION_EVIDENCE_GATE_NOT_BUY_SIGNAL`
- `MANUAL_CONDITION_RISK_DISPOSITION_NOT_DIAGNOSIS_OR_BUY_SIGNAL`

## Estados

Para lotes con peritaje público:

- el workflow v0.29 sigue siendo la autoridad;
- el nuevo gate queda `NOT_APPLICABLE`;
- un peritaje existente que no está `REVIEWED` sigue generando `PERITAJE_NOT_REVIEWED`.

Para lotes sin peritaje público:

- sin disposición: `UNREVIEWED`;
- disposición guardada como borrador: `DRAFT`;
- continuar bajo incertidumbre: `REVIEWED_ACCEPT`;
- declinar por falta de evidencia: `REVIEWED_DECLINE`.

## Disposiciones permitidas

### `ACCEPT_UNKNOWN_WITH_RESERVE`

Significa únicamente:

- la persona autorizada reconoce expresamente que no existe peritaje público;
- documenta qué información sí revisó y qué información falta;
- acepta continuar el análisis bajo esa incertidumbre.

No significa:

- que el vehículo esté en buen estado;
- que no requiera reparaciones;
- que sea seguro comprarlo;
- que exista un diagnóstico mecánico;
- que el sistema recomiende ofertar.

Además, `REVIEWED_ACCEPT` **no es suficiente para readiness**. El lote debe tener una reserva de reparación positiva en sus costos revisados.

Si falta esa reserva aparece:

- blocker `CONDITION_REPAIR_RESERVE_MISSING`;
- `next_action = REVIEW_CONDITION_RESERVE`;
- la UI enruta a Costos del mismo lote.

### `DECLINE_UNKNOWN_CONDITION`

Significa que la falta de evidencia física es suficiente para detener el caso bajo el criterio humano aplicado.

Genera:

- blocker `CONDITION_RISK_DECLINED`;
- `next_action = NO_ACTION_CONDITION_DECLINED`;
- stage `CONDITION_DECLINED_NO_ACTION`;
- rank 990.

Así el lote no se marca READY y tampoco compite falsamente como trabajo urgente.

## Evidencia requerida

Una disposición `REVIEWED` exige:

- lote válido;
- ausencia real de un attachment público `PERITAJE`;
- una de las dos disposiciones permitidas;
- nota de evidencia/fundamento de al menos 20 caracteres.

Si aparece posteriormente un peritaje público, el RPC rechaza el uso del workflow alternativo y la UI redirige al workflow canónico de peritaje.

## Modelo de datos

### `lot_condition_dispositions`

Estado actual, uno por lote.

Campos principales:

- `lot_id`;
- `external_lot_id`;
- `disposition`;
- `evidence_note`;
- `reviewed_at`;
- timestamps;
- interpretación fija.

### `lot_condition_disposition_history`

Registro append-only de cada escritura humana:

- disposición;
- nota;
- si fue marcada `REVIEWED`;
- fecha;
- interpretación fija.

Ambas tablas:

- tienen RLS;
- no conceden acceso a `public`, `anon` ni `authenticated`;
- son operadas por backend con `service_role`.

## RPC

`dashboard_save_condition_disposition`

Autoridad estrictamente limitada a la disposición de condición.

No modifica:

- `final_decision`;
- Fasecolda;
- evidencia de mercado;
- costos del lote;
- puja actual;
- puja máxima;
- ROI;
- recomendación de compra.

El resultado devuelve explícitamente:

- `buy_signal = false`;
- `economic_fields_modified = false`.

## Readiness

v0.49 conserva el contrato de columnas histórico y agrega provenance de condición al final.

Blockers nuevos:

1. `CONDITION_RISK_UNREVIEWED`
2. `CONDITION_RISK_DECLINED`
3. `CONDITION_REPAIR_RESERVE_MISSING`

Orden de trabajo relevante:

`Fasecolda → comisión → peritaje existente / condición desconocida → mercado → costos → reserva condición → puja → decisión disponible`

Un lote únicamente llega a `READY_FOR_DECISION` cuando no queda ningún blocker.

Esto sigue sin ser una señal de compra.

## Due Diligence

`dashboard_due_diligence_queue` conserva el contrato v0.46 y agrega provenance de condición al final.

La UI v0.49:

- muestra estado de condición separado del peritaje;
- enlaza `REVIEW_CONDITION_RISK` al nuevo workflow;
- enlaza `REVIEW_CONDITION_RESERVE` a Costos;
- muestra `CONDITION_DECLINED_NO_ACTION` como estado de no-acción;
- mantiene el contexto exacto de lote;
- sigue sin autoridad de escritura de negocio.

## Condition Review Dashboard

Nueva Edge Function:

`superbid-condition-review-dashboard`

Capacidades:

- cola de lotes activos sin peritaje público;
- detalle canónico por lote;
- histórico de disposiciones;
- DRAFT y REVIEWED;
- autenticación privada server-side;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- transporte de contexto limitado a `external_lot_id` de 5–12 dígitos;
- salida REVIEWED al readiness canónico del mismo lote.

Únicos RPC visibles desde esta función:

- `dashboard_token_valid`;
- `dashboard_save_condition_disposition`.

## Completion safety

El detalle no depende únicamente de la cola pendiente.

Consulta `dashboard_economic_readiness_current` por lote, por lo cual puede explicar correctamente si:

- la disposición ya fue revisada;
- el blocker cambió a reserva faltante;
- apareció un peritaje público;
- el lote cambió de estado.

No interpreta desaparición de una cola como éxito automático.

## Impacto esperado sobre la producción actual

Antes de aplicar v0.49:

- 403 lotes en readiness;
- 0 `READY_FOR_DECISION`;
- 108 casos de costos activos sin peritaje público;
- 24 casos previamente clasificados como fast-lane tenían también peritaje `NOT_AVAILABLE`.

Después de la migración, esos casos deben adquirir un gate explícito de condición. No se crearán disposiciones automáticamente.

Por tanto:

- el número total de lotes no cambia por la migración;
- ningún lote debe convertirse automáticamente en READY;
- deben existir 0 disposiciones creadas por deploy;
- los casos sin peritaje deben quedar operables mediante el nuevo workflow.

Los conteos BLOCKED/CLOSED pueden variar mientras corre el despliegue por el paso natural del tiempo y cierre de subastas; esa variación debe distinguirse de escrituras de negocio.

## Despliegue

Orden requerido después de CI y merge certificados:

1. aplicar `20260826003500_condition_evidence_gate_v49.sql`;
2. desplegar `superbid-condition-review-dashboard`;
3. desplegar `superbid-readiness-dashboard` actualizado;
4. preservar la configuración de autenticación productiva de cada Edge Function;
5. certificar vistas, funciones, conteos y cero escrituras accidentales.

No crear datos ficticios para superar el gate.

## Criterios de aceptación

1. Falta de peritaje público produce blocker real.
2. Peritaje público existente conserva el workflow v0.29.
3. DRAFT no resuelve el gate.
4. REVIEWED requiere nota suficiente.
5. `ACCEPT_UNKNOWN_WITH_RESERVE` no diagnostica ni genera buy signal.
6. Aceptación sin reserva positiva sigue bloqueada.
7. `DECLINE_UNKNOWN_CONDITION` permanece bloqueado y pasa a no-acción.
8. Condition dashboard conserva lote en autenticación.
9. No hay open redirects.
10. Condition dashboard solo tiene el RPC de disposición además de autenticación.
11. Readiness sigue sin escritura de negocio.
12. Contratos históricos se preservan y las columnas nuevas se anexan.
13. Package version = `0.49.0`.
14. Suite histórica completa PASS.
15. Producción no recibe disposiciones automáticas durante migración/deploy.
