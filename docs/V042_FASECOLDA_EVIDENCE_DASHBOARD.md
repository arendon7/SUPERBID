# v0.42 — Dashboard del lifecycle de evidencia Fasecolda

## Objetivo

Hacer visible el lifecycle v0.41 sin duplicar lógica de negocio ni añadir nuevas escrituras.

Nueva Edge Function privada:

`superbid-fasecolda-evidence-dashboard`

Guardrail:

`FASECOLDA_YEAR_EVIDENCE_CHANGE_NOT_VALUATION`

## Vista Lifecycle

Ruta raíz:

`/functions/v1/superbid-fasecolda-evidence-dashboard`

Muestra por caso lógico:
- último evento de evidencia;
- fecha de cambio;
- estado `REVIEW_REQUIRED / DISPOSITION_CURRENT / OPEN_REVIEW`;
- siguiente acción de lifecycle;
- vehículo/año;
- años disponibles en fuente;
- lotes cubiertos;
- disposición v0.40 vigente cuando corresponde.

Filtros:
- estado de revisión;
- evento (`NEW / CHANGED / REOPENED / UNCHANGED`);
- razón diagnóstica.

## Vista Eventos

`/functions/v1/superbid-fasecolda-evidence-dashboard/events`

Expone el historial de eventos backend:
- `NEW`;
- `UNCHANGED`;
- `CHANGED`;
- `RESOLVED`;
- `REOPENED`.

Incluye logical key, fingerprint anterior/actual, razón anterior/actual, número de lotes y marcador de importación de la fuente.

## Seguridad

- login privado mediante `dashboard_token_valid`;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- server-rendered;
- sin JavaScript cliente;
- después del login solo admite GET;
- no contiene RPC de disposición, matching, costos ni peritajes.

## Semántica

Los badges de lifecycle organizan atención humana. Nunca:
- crean homologación;
- interpolan años;
- escriben valor Fasecolda;
- modifican puja máxima;
- modifican ROI;
- modifican decisión final.

`RESOLVED` solo significa que el logical case dejó de estar presente en la cola diagnóstica por año. No implica automáticamente que ahora exista un match `HIGH`.

## Relación con v0.40

La pantalla enlaza al dashboard v0.40 para realizar una disposición humana cuando corresponda. v0.42 por sí sola es completamente read-only.
