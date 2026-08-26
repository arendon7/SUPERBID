# SUPERBID v0.54 — Fasecolda Search Exploration Matrix

## Objetivo

Reducir el trabajo manual del workflow `SEARCH_TERM_WORKFLOW` sin convertir heurísticas de texto ni resultados de búsqueda pública en homologaciones Fasecolda.

v0.54 reemplaza el flujo de un solo probe por una matriz acotada de hipótesis de búsqueda. La matriz es una ayuda operativa: no persiste sus resultados, no selecciona un término ganador y no modifica candidatos, match, referencia efectiva, costos, ROI, max bid ni decisión final.

Guardrail principal:

`AUTOMATED_SEARCH_VARIANT_NOT_OVERRIDE_OR_MATCH`

Guardrails heredados:

- `FASECOLDA_SEARCH_PROBE_NOT_MATCH`
- `MANUAL_FASECOLDA_SEARCH_TERM_NOT_MATCH`
- `CASE_CONTEXT_ROUTING_NOT_BUY_SIGNAL`

## Baseline productiva previa a v0.54

Dentro de los 153 casos cuyo primer paso era `REVIEW_VALUATION`:

- 99 estaban en `CANDIDATE_RESOLUTION`;
- 39 estaban en `SEARCH_TERM_WORKFLOW`;
- 15 estaban en `YEAR_REFERENCE_WORKFLOW`.

En los 39 casos de búsqueda:

- 24 tenían match `UNMATCHED` y diagnóstico `SEARCH_TERM_CAN_BE_EXPANDED`;
- 15 no tenían fila de match (`NO_MATCH_ROW`);
- 39/39 tenían `candidate_count = 0`;
- 39/39 tenían `suggested_search_term` distinto del término actual;
- 0 tenían override manual activo;
- 39 tenían `brand` no nulo;
- 37 tenían `model_year`.

Ejemplos observados:

- `TOYOTA COROLLA` → `TOYOTA COROLLA CROSS`;
- `VOLKSWAGEN T` → `VOLKSWAGEN T CROSS`;
- `NISSAN X` → `NISSAN X TRAIL`;
- `CHEVROLET TRAIL` → `CHEVROLET TRAIL BLAZER`;
- `JMC VIGUS` → `JMC VIGUS PLUS`.

También existen casos que no son realmente un problema de búsqueda sino de identidad de entrada, por ejemplo títulos/brands canónicos como `COMBO:`, `VOLQUETA`, `AUTOMÓVIL` o `CAMIÓN`. El RPC v0.35 exige conservar `auction_lots.brand`; intentar resolver esos casos fabricando un término sería conceptualmente incorrecto.

## Disposición fail-closed

El helper puro `search_exploration.ts` clasifica cada caso en una de tres disposiciones:

1. `EXPLORABLE`: existe año y la marca canónica permite construir términos seguros que preservan dicha marca.
2. `IDENTITY_INPUT_REVIEW`: la marca está vacía, es genérica/contaminada o el término sugerido contradice la marca canónica.
3. `MISSING_YEAR`: no existe un año de modelo válido.

Solo `EXPLORABLE` puede llegar a un probe, tanto desde la matriz como desde el formulario manual. Esta condición se revalida en servidor inmediatamente antes de invocar el RPC de probe o el RPC de override. Ocultar un botón en UI no es considerado una barrera de seguridad suficiente.

## Generación de variantes

Las variantes se calculan determinísticamente en memoria y nunca se guardan.

Orden:

1. término actual;
2. término sugerido existente;
3. prefijos adicionales derivados literalmente del título después de la marca canónica.

Reglas:

- máximo 4 variantes (`MAX_SEARCH_VARIANTS = 4`);
- deduplicación exacta después de normalización;
- cada término debe preservar la marca canónica;
- se detiene la expansión al encontrar señales técnicas como cc, transmisión, tracción, combustible, placa, RP o `MOD`;
- no existe score de variantes;
- no existe `best_term`, `winner`, `recommended_term` ni preselección.

## Search Exploration Matrix

Para un caso `EXPLORABLE`, el operador puede ejecutar `Explorar N variantes`.

El Edge Function:

1. vuelve a cargar el caso vigente;
2. vuelve a clasificarlo;
3. si dejó de ser `EXPLORABLE`, responde fail-closed y ejecuta cero probes;
4. ejecuta las variantes secuencialmente, nunca en bulk paralelo;
5. cada llamada usa exclusivamente `dashboard_probe_fasecolda_search_term`;
6. muestra por término HTTP, cantidad de códigos y hasta 22 códigos devueltos por la fuente pública.

La cantidad de códigos no se interpreta como score de calidad. Que un término devuelva códigos tampoco significa que describa correctamente el vehículo.

## Override humano

Solo un resultado concreto que devolvió códigos puede mostrar el formulario de confirmación.

La UI v0.54 exige:

- fundamento humano de al menos 10 caracteres;
- checkbox explícito;
- un único término por confirmación.

El servidor vuelve a comprobar que el caso continúe `EXPLORABLE` antes de llamar `dashboard_set_fasecolda_search_term_override`.

El RPC v0.36 conserva su autoridad original:

- vuelve a ejecutar el probe;
- solo acepta términos que devuelvan códigos públicos;
- persiste el override manual;
- reejecuta el matcher normal;
- no fuerza estado `HIGH`;
- no selecciona código Fasecolda;
- mantiene histórico reversible mediante `CLEAR`.

## Autoridad

El dashboard v0.54 solo referencia tres RPCs:

- `dashboard_token_valid`;
- `dashboard_probe_fasecolda_search_term`;
- `dashboard_set_fasecolda_search_term_override`.

No incorpora RPC nuevo, tabla nueva, view nueva ni migración.

No modifica directamente:

- `lot_fasecolda_matches`;
- `lot_fasecolda_candidates`;
- resolución manual de candidato;
- evidencia v0.52;
- market evidence;
- costos;
- ROI;
- max bid;
- final decision.

## Edge CI

v0.54 extiende el gate v0.51. Además de ejecutar `deno check` sobre todos los `supabase/functions/*/index.ts`, `scripts/check_edge_functions.sh` descubre dinámicamente archivos `*_test.ts` y ejecuta `deno test`.

El primer helper cubierto es `search_exploration_test.ts`, con casos para:

- límite de cuatro variantes;
- deduplicación;
- Toyota Corolla/Cross;
- expansión de HB20S/Accent sin cruzar `AT`;
- bloqueo de `COMBO`, `VOLQUETA` y `AUTOMÓVIL`;
- contradicción de marca;
- ausencia de año.

Así la lógica pura de Edge deja de depender únicamente de tests Python que inspeccionan strings.

## Despliegue

v0.54 no requiere migración de base de datos.

Proceso requerido:

1. pytest completo PASS;
2. 14/14 Edge entrypoints `deno check` PASS;
3. tests Deno del helper PASS;
4. branch 0 detrás de `main`;
5. merge con SHA de head certificado;
6. CI de `main` PASS;
7. snapshot productivo previo;
8. despliegue únicamente de `superbid-fasecolda-search-dashboard` desde el merge SHA inmutable con `verify_jwt=false`;
9. lectura de la fuente realmente desplegada;
10. snapshot postdeploy y verificación de cero overrides/eventos creados por el despliegue.

No se considerará completada una UAT de navegador si el runtime no puede alcanzar externamente el endpoint.
