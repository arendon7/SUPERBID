# v0.40 — Disposición auditable de casos Fasecolda por año

## Objetivo

Reducir trabajo humano repetido en los diagnósticos `NO_YEAR_COMPATIBLE_REFERENCE` sin convertir referencias de años vecinos en una valoración del año faltante.

Guardrail:

`FASECOLDA_YEAR_GAP_DISPOSITION_NOT_VALUATION`

## Fingerprint de evidencia

Los lotes con evidencia materialmente idéntica se agrupan en un `case_key` determinístico. El fingerprint incorpora identidad buscada, año del lote, razón diagnóstica, años disponibles, referencias inferior/superior, rangos y códigos.

Si cambia la evidencia, cambia el fingerprint y una disposición anterior deja de aplicar al nuevo caso.

Esto evita revisar individualmente múltiples lotes que comparten exactamente el mismo hueco de cobertura.

## Disposiciones humanas

- `CONFIRM_COVERAGE_GAP`: confirma que la evidencia actual no contiene referencia del año requerido;
- `REQUEST_SOURCE_REFRESH`: solicita revisar/actualizar la fuente Fasecolda;
- `REFER_IDENTITY_REVIEW`: deriva un caso de inconsistencia de marca a revisión de identidad;
- `REQUEST_MATCHER_RECHECK`: solo para diagnósticos obsoletos donde ya apareció referencia del mismo año;
- `CLEAR`: retira una disposición y reabre el caso.

Cada acción se valida contra la razón diagnóstica. Por ejemplo, un caso de marca inconsistente no puede cerrarse como simple gap de cobertura.

## Persistencia y auditoría

- `fasecolda_year_reference_case_dispositions`: estado vigente por fingerprint;
- `fasecolda_year_reference_case_disposition_history`: historial inmutable de acciones;
- `dashboard_fasecolda_year_reference_case_queue`: cola agrupada;
- `dashboard_fasecolda_year_reference_lot_status`: proyección por lote del estado del caso.

RPC backend-only:

`dashboard_set_fasecolda_year_reference_case_disposition(case_key, action, note)`

## Semántica

`CONFIRM_COVERAGE_GAP` significa únicamente: con la evidencia Fasecolda importada y el fingerprint actual, no existe una referencia utilizable del mismo año.

No significa:
- interpolar valores;
- extrapolar años;
- adoptar el valor del año anterior o posterior;
- crear `HIGH`;
- modificar `fasecolda_current_cop`;
- modificar puja máxima, ROI o decisión final;
- desbloquear automáticamente readiness económico.

El lote puede permanecer bloqueado en `REVIEW_VALUATION` aunque el diagnóstico operativo esté reconocido.

## Dashboard

`superbid-fasecolda-year-dashboard` v0.40 muestra casos agrupados, número de lotes cubiertos, evidencia inferior/superior, estado operativo y acciones compatibles.

La interfaz es server-rendered, sin JavaScript cliente. Las escrituras pasan exclusivamente por la RPC backend-only.

## Fotografía inicial

La primera ejecución agrupó 29 diagnósticos de lote en 14 fingerprints de evidencia. Los 16 lotes `YEAR_GAP_BETWEEN_REFERENCES` quedaron condensados en 2 casos.

La certificación inicial debe realizarse sin guardar disposiciones reales: tablas de disposición e historial deben permanecer en cero hasta una revisión humana efectiva.
