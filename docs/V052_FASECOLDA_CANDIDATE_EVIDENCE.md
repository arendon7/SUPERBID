# SUPERBID v0.52 — Fasecolda Candidate Resolution Evidence

## Problema

La referencia Fasecolda efectiva puede convertirse en `HIGH / MANUAL_CONFIRMED` cuando un operador escoge un candidato. Esa acción modifica una entrada material del modelo económico, por lo que una nota libre no es evidencia suficiente para distinguir versiones exactas.

Snapshot de diseño previo a v0.52:

- 99 casos activos de `CANDIDATE_RESOLUTION` con candidatos reales y sin resolución manual vigente.
- En esos 99 casos, `auction_lots.version`, `engine_cc`, `fuel`, `transmission` y `drivetrain` están vacíos.
- 76/99 tienen al menos un anexo público registrado.
- 54/99 tienen peritaje público.
- Hay empates o gaps mínimos de score entre candidatos materialmente distintos: motor, transmisión, combustible, trim y uso cargo/pasajeros, entre otros.
- Algunos códigos candidatos comparten exactamente año y descripción, por lo que el payload disponible no permite distinguir un código exacto de otro.

Conclusión: el matcher puede producir candidatos y priorización, pero no puede promover una versión exacta sin evidencia humana adicional.

## Invariante

`MANUAL_FASECOLDA_CANDIDATE_EVIDENCE_NOT_AUTOMATIC_MATCH_OR_BUY_SIGNAL`

v0.52 no crea una recomendación de compra. No cambia costos, mercado, bid, max bid, ROI ni decisión final. El match automático se conserva por separado.

## Evidencia estructurada

Cada candidato en REVIEWED exige seis dimensiones:

1. `line_identity`
2. `engine_cc`
3. `transmission`
4. `fuel`
5. `drivetrain`
6. `trim_body_use`

Estados permitidos por dimensión:

- `MATCH`: la fuente sustenta que el atributo coincide con el candidato.
- `CONFLICT`: la fuente contradice al candidato.
- `NOT_STATED`: la fuente no declara el atributo. No equivale a match.

Cada dimensión REVIEWED exige:

- estado;
- fuente;
- fundamento humano de al menos 10 caracteres;
- valor observado para `MATCH` o `CONFLICT`.

Fuentes válidas backend-side:

- URL pública canónica del mismo lote;
- URL de un `lot_attachment` registrado para el mismo `lot_id`.

La UI no puede convertir una URL arbitraria en evidencia aceptada.

## Gate REVIEWED

Una confirmación exacta solo es válida cuando:

- las 6 dimensiones están completas;
- `line_identity=MATCH`;
- `conflict_count=0`;
- existe al menos un `MATCH` discriminante adicional a la línea;
- existe resumen humano de al menos 20 caracteres;
- el candidato sigue perteneciendo al set actual del lote;
- el año coincide;
- tiene valor Fasecolda utilizable;
- pasa el identity guard histórico;
- no existe otro candidato actual, de igual año, con la misma descripción normalizada.

El último punto evita escoger arbitrariamente entre códigos que el dataset actual no permite distinguir.

## DRAFT

DRAFT puede estar incompleto.

Guardar DRAFT:

- no llama al RPC histórico de resolución manual;
- no cambia el match efectivo;
- conserva `match_origin=AUTOMATIC`;
- no es buy signal.

Si ya existe una resolución manual, no puede degradarse silenciosamente la evidencia a DRAFT. Primero debe hacerse CLEAR explícito.

## Compatibilidad con v0.33

El RPC histórico `dashboard_set_fasecolda_manual_resolution` se conserva para compatibilidad e historial, pero ya no puede crear ni actualizar una resolución manual por sí solo.

Trigger `trg_fasecolda_candidate_evidence_gate_v52` exige que toda escritura en `lot_fasecolda_manual_resolutions` corresponda exactamente con un snapshot v0.52 REVIEWED vigente.

Por tanto, incluso un caller legacy que intente `CONFIRM` queda bloqueado si no pasó el gate de evidencia.

## CLEAR e invalidación

`dashboard_clear_fasecolda_candidate_resolution_v52` exige nota humana de al menos 10 caracteres y usa el CLEAR histórico.

Al eliminar una resolución manual:

- el snapshot actual de evidencia se invalida;
- se preserva en histórico como `MANUAL_REMOVAL_INVALIDATED`.

Si cambian `title`, `brand`, `line` o `model_year`:

- la evidencia actual se invalida;
- el histórico registra `IDENTITY_CHANGE_INVALIDATED`;
- el trigger v0.33 mantiene su propia invalidación de la resolución manual.

## Cockpit

Edge Function nueva:

`superbid-fasecolda-candidate-cockpit`

Propiedades:

- autenticación privada con `dashboard_token_valid`;
- cookie propia `HttpOnly; Secure; SameSite=Strict`;
- lot context exclusivamente numérico 5–12 dígitos;
- detalle completion-safe consultando tablas canónicas, no solo la cola pendiente;
- comparación de candidatos sin preselección automática;
- selección explícita de un código antes de cargar evidencia;
- evidencia previa solo se precarga si pertenece al mismo código seleccionado;
- fuentes visibles y ligadas al lote;
- DRAFT permanece en el mismo caso;
- REVIEWED retorna el mismo lote a Readiness;
- CLEAR reabre el caso de forma explícita.

Business-write RPCs visibles desde esta Edge Function:

- `dashboard_save_fasecolda_candidate_resolution`
- `dashboard_clear_fasecolda_candidate_resolution_v52`

Además usa `dashboard_token_valid` exclusivamente para autenticación.

No expone writes de costos, mercado, peritaje, bid, ROI o decisión final.

## Retiro del resolver legacy

`superbid-fasecolda-dashboard` deja de contener la vieja UI de CONFIRM/CLEAR.

Se convierte en un shim de compatibilidad que:

- acepta únicamente `lot` numérico validado;
- no usa service role;
- no llama RPCs;
- redirige al nuevo cockpit conservando únicamente el lote.

Esto mantiene enlaces históricos sin conservar una superficie de escritura que pueda intentar saltarse el gate v0.52.

## Permisos

Tablas nuevas:

- `lot_fasecolda_candidate_resolution_evidence`
- `lot_fasecolda_candidate_resolution_evidence_history`

Ambas:

- RLS enabled;
- sin acceso `public`, `anon` o `authenticated`;
- acceso backend `service_role` únicamente.

Vista:

- `dashboard_fasecolda_candidate_resolution_cockpit_v52`
- `service_role` only.

RPCs v0.52:

- `service_role` only.

## Release gates

Antes de merge:

1. full historical pytest suite PASS;
2. v0.52 regression suite PASS;
3. `deno check` sobre todas las Edge Functions PASS;
4. branch 0 detrás de `main`;
5. revisión de diff sin autoridad económica nueva.

Antes de producción:

1. snapshot de readiness y manual resolutions;
2. aplicar migración exacta desde merge SHA;
3. verificar tablas/RPC/view/permissions;
4. smoke transaccional con rollback si se requiere validar RPC sin dejar evidencia ficticia;
5. desplegar primero `superbid-fasecolda-candidate-cockpit`;
6. desplegar luego el shim legacy;
7. ambos `ACTIVE`, manteniendo `verify_jwt=false` cuando la función implemente autenticación custom; el shim no expone datos ni business writes;
8. verificar 0 nuevas resoluciones/evidencias generadas por despliegue;
9. comprobar que readiness no cambió por efecto del release.

## No objetivos

v0.52 no:

- interpreta automáticamente PDFs;
- extrae automáticamente atributos y los confirma;
- elige el best score;
- convierte `NOT_STATED` en match;
- resuelve candidatos duplicados por heurística;
- genera buy signal;
- modifica campos económicos.
