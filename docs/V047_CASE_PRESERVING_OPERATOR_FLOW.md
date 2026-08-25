# v0.47 — Case-Preserving Operator Flow

## Contexto

v0.46 convirtió Readiness en el Due Diligence Command Center y corrigió el enrutamiento hacia los workflows especializados de mercado, costos, peritaje y Fasecolda.

La auditoría posterior encontró el siguiente cuello de botella productivo:

- 403 lotes en readiness;
- 286 `BLOCKED`;
- 117 `CLOSED`;
- 0 `READY_FOR_DECISION`;
- 192 de los 286 bloqueados tienen `REVIEW_VALUATION` como primera acción;
- 66 tienen `REVIEW_PERITAJE`;
- 24 tienen `VALIDATE_MARKET`;
- 4 tienen `REVIEW_COMMISSION`.

Dentro de los 192 casos de valoración, el workbench productivo los distribuye actualmente así:

- `CANDIDATE_RESOLUTION` rank 10: 54;
- `CANDIDATE_RESOLUTION` rank 20: 67;
- `SEARCH_TERM_WORKFLOW` rank 30: 30;
- `SEARCH_TERM_WORKFLOW` rank 40: 20;
- `YEAR_REFERENCE_REVIEW` rank 50: 21.

Los conteos son una fotografía operacional y no son invariantes de código.

## Defecto corregido

Antes de v0.47, seleccionar un lote en Readiness y abrir Fasecolda llevaba al workbench global. Desde ahí, abrir el resolver de candidatos, diagnóstico de término, revisión por año o lifecycle volvía a entrar a una cola global.

El operador tenía que reencontrar manualmente el vehículo en cada superficie. Con cientos de casos activos, esto generaba:

- fricción operacional innecesaria;
- pérdida de continuidad cognitiva;
- riesgo de revisar o modificar el caso equivocado;
- dificultad para validar un recorrido completo de un lote desde blocker hasta resolución.

Además, cada Edge Function mantiene su propia cookie privada. Por ello, incluso un enlace futuro con contexto podía perder el lote al pasar por el login de un módulo sin sesión previa.

## Objetivo v0.47

Hacer que un `external_lot_id` seleccionado viaje de punta a punta por el flujo operador:

`Readiness → Fasecolda Workbench → Resolver / Search / Year / Evidence → regreso al mismo caso`

El contexto también debe sobrevivir:

- filtros dentro de la página;
- autenticación privada del módulo de destino;
- confirmación manual válida;
- retiro de una resolución manual;
- confirmación de override de término;
- guardado de una disposición por año.

## Principio de seguridad

El parámetro de navegación es únicamente:

`lot=<external_lot_id>`

Reglas:

1. solo se acepta un identificador numérico de 5 a 12 dígitos;
2. un valor inválido se descarta;
3. nunca se acepta `return_to`, `redirect_uri`, `redirect_url` o una URL arbitraria suministrada por el navegador;
4. las rutas de regreso se construyen server-side con destinos internos conocidos;
5. el contexto de UI no cambia ninguna autoridad económica.

Guardrail:

`CASE_CONTEXT_ROUTING_NOT_BUY_SIGNAL`

Preservar un lote solo significa preservar contexto de trabajo. No implica mejor oportunidad, compra, puja autorizada, match HIGH, ROI aceptable ni decisión económica.

## Superficies v0.47

### 1. Due Diligence Command Center

`superbid-readiness-dashboard`

- acepta `?lot=<id>`;
- filtra `dashboard_due_diligence_queue` por `external_lot_id`;
- conserva el lote al aplicar filtros;
- `REVIEW_VALUATION` abre `superbid-fasecolda-workbench?lot=<id>`;
- el shortcut Fasecolda hace lo mismo;
- el login conserva únicamente el lote validado.

No cambia:

- `due_diligence_rank`;
- blockers;
- readiness;
- `max_bid_market_validated_cop`;
- ROI;
- `final_decision`.

### 2. Fasecolda Valuation Workbench

`superbid-fasecolda-workbench`

- acepta y filtra por lote exacto;
- calcula sus métricas sobre el mismo lote cuando está en modo caso;
- conserva el lote en filtros y autenticación;
- envía el identificador exacto a cada workflow secundario.

Routing:

- `CANDIDATE_RESOLUTION` → resolver con `lot=<id>`;
- `SEARCH_TERM_WORKFLOW` → search con `lot=<id>`;
- workflows `YEAR_*` → year con `lot=<id>`;
- `KNOWN_YEAR_COVERAGE_GAP` → evidence con `lot=<id>`;
- fallback → readiness con `lot=<id>`.

El workbench sigue siendo read-only respecto de decisiones de negocio.

### 3. Resolver de candidatos

`superbid-fasecolda-dashboard`

- restringe `dashboard_fasecolda_resolution_queue` al `external_lot_id` seleccionado;
- no preselecciona candidatos;
- mantiene confirmación humana explícita;
- conserva el RPC `dashboard_set_fasecolda_manual_resolution`;
- después de `CONFIRM` vuelve al mismo lote;
- después de `CLEAR` vuelve al mismo lote;
- si el módulo exige login, el lote se transporta como un campo numérico validado, no como URL.

No cambia la separación entre:

- match automático;
- proveniencia automática;
- resolución manual efectiva.

### 4. Diagnóstico de término de búsqueda

`superbid-fasecolda-search-dashboard`

- filtra `dashboard_fasecolda_unmatched_diagnostics` por lote;
- mantiene `dashboard_probe_fasecolda_search_term` como probe sin homologación;
- mantiene `dashboard_set_fasecolda_search_term_override` como único write de término;
- después de confirmar override, vuelve al mismo lote;
- el matcher normal sigue siendo quien decide el resultado.

No se fuerza un match HIGH.

### 5. Casos Fasecolda por año

`superbid-fasecolda-year-dashboard`

Los casos están agrupados y contienen `external_lot_ids[]`, por lo que el modo caso usa el operador PostgREST `cs` para exigir que el arreglo contenga el lote seleccionado.

- los conteos se restringen al mismo lote;
- el listado se restringe al mismo lote;
- `return_lot` es únicamente un ID numérico validado;
- el servidor construye el redirect interno después de una disposición;
- no existe redirect arbitrario.

El RPC de escritura sigue siendo exactamente:

`dashboard_set_fasecolda_year_reference_case_disposition`

No interpola años ni crea una valoración.

### 6. Lifecycle de evidencia

`superbid-fasecolda-evidence-dashboard`

- el estado actual filtra `external_lot_ids[]` por pertenencia del lote;
- los accesos a lotes vuelven al workbench del caso exacto;
- `Revisar caso` abre Year con el mismo lote;
- el login conserva el lote validado;
- la vista de eventos permanece explícitamente global porque el contrato agregado de eventos no expone un identificador individual confiable para filtrar por lote.

No se fabrica una correlación de evento por vehículo que el backend no garantice.

## Autenticación

Se conserva el patrón existente de todas las superficies:

- `dashboard_token_valid` server-side;
- `SUPABASE_SERVICE_ROLE_KEY` solo en Edge Runtime;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- sin service role en navegador.

v0.47 añade preservación segura del lote a través del login:

- la URL de login puede incluir exclusivamente el `lot` ya validado, o el resolver puede transportarlo como hidden field validado;
- después de autenticar el servidor reconstruye una ruta interna conocida;
- no hay open redirect.

## Autoridad de escritura

v0.47 no crea migraciones, tablas, vistas, triggers ni RPC nuevos.

Los únicos RPC de negocio presentes en las superficies modificadas siguen siendo los que ya existían:

- resolver: `dashboard_set_fasecolda_manual_resolution`;
- search: `dashboard_probe_fasecolda_search_term` y `dashboard_set_fasecolda_search_term_override`;
- year: `dashboard_set_fasecolda_year_reference_case_disposition`.

Readiness, Workbench y Evidence continúan sin RPC de escritura de negocio.

## Criterios de aceptación

1. Un lote seleccionado en Readiness llega al Fasecolda Workbench con el mismo ID.
2. El Workbench filtra por ese ID y lo propaga a todos sus child workflows.
3. Resolver y Search filtran por `external_lot_id` exacto.
4. Year y Evidence filtran casos agregados por pertenencia en `external_lot_ids[]`.
5. Los filtros GET preservan el lote.
6. La autenticación privada preserva el lote válido.
7. Un lote inválido no se utiliza para filtrar ni redirigir.
8. No existe ningún parámetro de redirect arbitrario.
9. Confirmar/retirar resolución manual regresa al mismo lote.
10. Confirmar override de término regresa al mismo lote.
11. Guardar una disposición por año regresa al mismo lote.
12. Las RPC de negocio permitidas no se amplían.
13. Cookies y validación server-side permanecen intactas.
14. No existe migración v0.47.
15. El paquete queda versionado como `0.47.0`.
16. La suite histórica completa debe seguir verde.

## Despliegue

v0.47 requiere desplegar únicamente las Edge Functions modificadas, fijadas al SHA inmutable del merge:

- `superbid-readiness-dashboard`;
- `superbid-fasecolda-workbench`;
- `superbid-fasecolda-dashboard`;
- `superbid-fasecolda-search-dashboard`;
- `superbid-fasecolda-year-dashboard`;
- `superbid-fasecolda-evidence-dashboard`.

No se ejecuta migración de base de datos.

## Certificación requerida

Antes del merge:

- branch `behind_by=0` respecto de `main`;
- tests v0.47 verdes;
- suite histórica completa verde;
- CI sobre merge sintético verde;
- revisión de que no aparezcan RPC nuevos ni rutas de redirect arbitrarias.

Después del merge:

- desplegar cada función desde el SHA exacto del merge;
- preservar `verify_jwt` conforme al estado productivo de cada función;
- comprobar que las seis funciones quedan `ACTIVE`;
- volver a consultar readiness para confirmar que un despliegue UI no alteró datos de negocio.
