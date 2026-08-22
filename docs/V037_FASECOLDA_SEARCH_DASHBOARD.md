# v0.37 — Dashboard de diagnóstico y término Fasecolda

## Objetivo

Convertir v0.34, v0.35 y v0.36 en un workflow humano privado sin mezclarlo con los dashboards operativos ya estables.

Nueva Edge Function:
`superbid-fasecolda-search-dashboard`

## Flujo

1. La portada consulta `dashboard_fasecolda_unmatched_diagnostics`.
2. El usuario revisa el término actual y el sugerido.
3. `Probar término` ejecuta únicamente `dashboard_probe_fasecolda_search_term`.
4. Si el probe no devuelve códigos públicos, no se muestra acción de confirmación.
5. Si `has_codes=true`, se habilita un formulario de confirmación explícita.
6. La confirmación llama `dashboard_set_fasecolda_search_term_override(...,'CONFIRM',...)`.
7. v0.36 reejecuta el matcher normal; la UI no calcula ni fuerza el estado resultante.

## Diagnósticos visibles

- `SEARCH_TERM_CAN_BE_EXPANDED`;
- `NO_MATCH_ROW`;
- `NO_YEAR_COMPATIBLE_REFERENCE`;
- `PUBLIC_SEARCH_RETURNED_NO_CODES`;
- `UNMATCHED_OTHER`.

## Overrides activos

`/overrides` lista los términos manuales vigentes y permite retirarlos con confirmación explícita. `CLEAR` vuelve a ejecutar el matcher con el término derivado del título.

## Guardrails

La UI muestra explícitamente:
- `FASECOLDA_UNMATCHED_DIAGNOSTIC_NOT_MATCH`;
- `FASECOLDA_SEARCH_PROBE_NOT_MATCH`;
- `MANUAL_FASECOLDA_SEARCH_TERM_NOT_MATCH`.

Un término, una sugerencia o un probe no son homologaciones. El override solo cambia la búsqueda y nunca fuerza `HIGH`.

## Seguridad

- autenticación con `dashboard_token_valid`;
- cookie propia `HttpOnly; Secure; SameSite=Strict`;
- server-rendered;
- sin JavaScript cliente;
- secretos solo en la Edge Function/service role.

## Certificación

Durante la certificación se validarán login, consulta de diagnósticos y presencia condicional de acciones sin ejecutar `CONFIRM` ni `CLEAR` sobre datos reales.
