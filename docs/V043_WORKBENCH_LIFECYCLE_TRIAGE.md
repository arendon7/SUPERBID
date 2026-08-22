# v0.43 — Workbench Fasecolda lifecycle-aware

## Objetivo

Hacer que el workbench de bloqueos `REVIEW_VALUATION` use el lifecycle de evidencia por año de v0.41 para decidir **qué requiere atención humana ahora** y qué no debe revisarse otra vez mientras la evidencia permanezca igual.

La capa sigue siendo de triage. No homologa vehículos, no crea valoraciones y no cambia la lógica económica.

## Problema que corrige

Antes de v0.43, un caso `NO_YEAR_COMPATIBLE_REFERENCE` podía seguir apareciendo en la misma cola operativa aun después de que una persona hubiera confirmado que el fingerprint vigente representaba un gap real de cobertura Fasecolda.

v0.43 diferencia la condición económica del trabajo operativo:

- el lote puede seguir bloqueado económicamente por falta de referencia compatible;
- pero si el gap ya fue revisado y la evidencia no cambió, no debe consumirse nuevamente tiempo humano;
- si el fingerprint cambia o reaparece evidencia relevante, el lifecycle vuelve a exigir revisión.

## Workflows y ranks

### Candidatos

- `CANDIDATE_RESOLUTION`, rank 10: 1–3 candidatos públicos;
- `CANDIDATE_RESOLUTION`, rank 20: más candidatos / evidencia insuficiente para HIGH.

### Referencias por año

- `YEAR_EVIDENCE_REVIEW`, rank 25: evidencia nueva, cambiada o reabierta;
- `YEAR_IDENTITY_REVIEW`, rank 32: disposición humana derivó el caso a identidad;
- `YEAR_MATCHER_RECHECK`, rank 33: se solicitó recheck del matcher;
- `YEAR_SOURCE_REFRESH_REQUESTED`, rank 35: se solicitó actualización de fuente;
- `YEAR_REFERENCE_REVIEW`, rank 50: caso de año sin disposición especializada;
- `KNOWN_YEAR_COVERAGE_GAP`, rank 85: gap confirmado para el fingerprint actual y disposición aún vigente.

### Búsqueda

- `SEARCH_TERM_WORKFLOW`, rank 30: término expandible;
- `SEARCH_TERM_WORKFLOW`, rank 40: `NO_MATCH_ROW`;
- rank 45 cuando la búsqueda pública no devuelve códigos.

## Regla crítica de lifecycle

Un `CONFIRM_COVERAGE_GAP` solo se considera vigente cuando:

- la disposición pertenece al `case_key` actual; y
- `evidence_review_status = DISPOSITION_CURRENT`.

En ese estado, el workbench lo envía a `KNOWN_YEAR_COVERAGE_GAP` con rank 85 y enlaza al dashboard de lifecycle de evidencia.

Si la evidencia cambia, v0.41 genera/reabre el caso y `evidence_review_status` vuelve a `REVIEW_REQUIRED`; entonces v0.43 lo eleva a `YEAR_EVIDENCE_REVIEW`, rank 25.

## Dashboard

`superbid-fasecolda-workbench` muestra ahora:

- workflow y rank;
- estado Fasecolda efectivo;
- candidatos;
- lifecycle de evidencia por año;
- evento vigente;
- siguiente acción de lifecycle;
- disposición humana vigente;
- diagnóstico y razón de triage;
- enlaces al workflow humano correspondiente.

El dashboard añade acceso directo a `superbid-fasecolda-evidence-dashboard`.

## Seguridad

- vista backend-only;
- `public`, `anon` y `authenticated` sin `SELECT` directo;
- solo `service_role` consulta la vista;
- dashboard server-rendered;
- cookie privada `HttpOnly; Secure; SameSite=Strict`;
- después del login solo se permiten lecturas;
- no existen RPC de matching, probe, override, disposición, costos o peritajes en este dashboard.

## Guardrails

`FASECOLDA_VALUATION_TRIAGE_NOT_MATCH`

`FASECOLDA_YEAR_EVIDENCE_CHANGE_NOT_VALUATION`

Un gap conocido puede dejar de requerir revisión repetida, pero **continúa bloqueado económicamente** hasta que exista evidencia suficiente para una valoración compatible. El lifecycle nunca fuerza `HIGH`, no escribe `fasecolda_current_cop`, no calcula puja máxima y no modifica ROI ni `final_decision`.
