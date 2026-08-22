# v0.41 — Lifecycle de evidencia Fasecolda por año

## Objetivo

Detectar cuándo cambia la evidencia que sustenta un diagnóstico de referencia Fasecolda por año, sin obligar al usuario a revisar repetidamente un gap conocido mientras la evidencia permanezca idéntica.

Guardrail:

`FASECOLDA_YEAR_EVIDENCE_CHANGE_NOT_VALUATION`

El lifecycle observa evidencia. Nunca calcula ni modifica una valoración.

## Dos identificadores distintos

### `logical_key`

Identifica de forma estable el problema vehículo/año usando:
- marca almacenada;
- marca del término de búsqueda;
- línea buscada;
- año del lote.

No contiene el fingerprint de evidencia. Por eso sobrevive a cambios de cobertura o códigos.

### `case_key`

Es el fingerprint v0.40 de la evidencia material actual: razón diagnóstica, años disponibles, referencias vecinas, rangos y códigos.

Cuando cambia `case_key` para el mismo `logical_key`, el sistema genera `CHANGED` y exige nueva revisión humana.

## Eventos

`fasecolda_year_reference_evidence_events` registra:
- `NEW`: aparece un logical case por primera vez;
- `UNCHANGED`: hubo una nueva importación Fasecolda pero el fingerprint material siguió igual;
- `CHANGED`: cambió el fingerprint para el mismo vehículo/año;
- `RESOLVED`: el logical case dejó de existir en la cola diagnóstica;
- `REOPENED`: un logical case previamente resuelto reaparece.

No se genera `UNCHANGED` en cada ejecución del cron. Solo cuando cambia el marcador de importación de la fuente y el fingerprint permanece idéntico.

## Estado actual

`fasecolda_year_reference_evidence_state` conserva un único estado por `logical_key`, incluyendo fingerprint actual/anterior, razón, número de lotes, marcador de importación, fechas y último evento.

## Relación con disposiciones v0.40

La vista `dashboard_fasecolda_year_reference_evidence_lifecycle` une el fingerprint actual con la disposición v0.40.

Una disposición solo es `DISPOSITION_CURRENT` si pertenece al `case_key` vigente. Si la evidencia cambia, el fingerprint cambia y la disposición anterior ya no se une al caso nuevo.

Para `CONFIRM_COVERAGE_GAP` con evidencia todavía idéntica:

`NO_REVIEW_UNTIL_EVIDENCE_CHANGES`

Esto reduce trabajo repetido pero no desbloquea el modelo económico.

## Automatización

`refresh_fasecolda_year_reference_evidence_v41()` corre cada 30 minutos mediante:

`fasecolda-year-evidence-v41`

La frecuencia permite reaccionar a imports, cambios de términos, identidad o matcher sin crear ruido. Una ejecución idempotente con fuente/fingerprint iguales no crea eventos.

## Seguridad

Estado, eventos, vistas y RPC son backend-only. `anon/authenticated` no tienen acceso directo.

## Semántica deliberada

El lifecycle nunca escribe:
- `lot_fasecolda_matches`;
- `fasecolda_current_cop`;
- confianza Fasecolda efectiva;
- puja máxima;
- ROI;
- `final_decision`.

`RESOLVED` significa que el caso dejó la cola diagnóstica por año. No afirma por sí solo que exista una valoración HIGH o que el vehículo sea una oportunidad de compra.

## Inicialización productiva

La primera ejecución creó 14 eventos `NEW`, correspondientes a 14 logical cases que cubren 29 lotes. Una segunda ejecución sin cambio de fuente/evidencia produjo cero eventos adicionales, confirmando idempotencia.

La certificación no creó ni modificó disposiciones humanas v0.40.
