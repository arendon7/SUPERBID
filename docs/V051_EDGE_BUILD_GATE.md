# v0.51 — Edge Build Gate

## Motivo

v0.50 expuso una brecha real del proceso de release: la suite Python completa podía estar verde y una Supabase Edge Function podía seguir siendo sintácticamente inválida para Deno/Supabase.

El caso concreto fue `superbid-peritaje-evidence-workbench`: dos backticks de Markdown dentro de un template literal TypeScript hicieron que el bundler de Supabase rechazara el despliegue, aunque 314/314 tests habían pasado.

v0.50.1 corrigió el defecto puntual. v0.51 corrige la causa sistémica: **ninguna Edge Function puede volver a llegar al merge gate sin ser parseada y type-checked por Deno**.

## Alcance

v0.51 es exclusivamente release engineering.

No agrega:

- migraciones;
- RPCs;
- tablas o vistas;
- permisos de negocio;
- cambios de `verify_jwt`;
- rutas productivas;
- señales de compra;
- escrituras económicas.

No requiere despliegue Supabase si el gate no obliga a corregir una función existente.

## Inventario protegido

Al iniciar v0.51 existen 13 directorios inmediatos bajo `supabase/functions`, todos con un `index.ts`:

1. `meli-oauth`;
2. `superbid-condition-review-dashboard`;
3. `superbid-cost-governance-dashboard`;
4. `superbid-dashboard`;
5. `superbid-fasecolda-dashboard`;
6. `superbid-fasecolda-evidence-dashboard`;
7. `superbid-fasecolda-search-dashboard`;
8. `superbid-fasecolda-workbench`;
9. `superbid-fasecolda-year-dashboard`;
10. `superbid-market-review-dashboard`;
11. `superbid-peritaje-evidence-workbench`;
12. `superbid-read-api`;
13. `superbid-readiness-dashboard`.

La implementación no congela esta lista: la descubre dinámicamente en cada ejecución.

## Toolchain reproducible

GitHub Actions usa:

- `denoland/setup-deno` v2.0.5, pinneado al commit `22d081ff2d3a40755e97629de92e3bcbfa7cf2ed`;
- Deno `2.9.5`.

El pin evita que el comportamiento del gate cambie silenciosamente por mover un tag de Action o por tomar una versión distinta de Deno.

## Script canónico

`scripts/check_edge_functions.sh`

El script:

1. usa `set -euo pipefail`;
2. exige que `deno` exista;
3. exige que exista `supabase/functions`;
4. descubre `supabase/functions/*/index.ts` en orden estable;
5. falla si no descubre ninguna función;
6. cuenta directorios inmediatos y entrypoints;
7. falla si algún directorio de función no tiene exactamente el entrypoint canónico esperado;
8. ejecuta `deno check --quiet` sobre cada `index.ts`;
9. identifica por nombre la función que falla;
10. termina con error en el primer fallo.

La comprobación es read-only: no despliega, no escribe base de datos y no usa credenciales de producción.

## CI

`.github/workflows/ci.yml` queda con dos jobs independientes.

### `test`

Conserva la suite Python histórica:

- Python 3.12;
- `pip install -e ".[dev]"`;
- `pytest -q`.

### `edge-build`

Nuevo gate:

- checkout;
- instalación pinneada de Deno 2.9.5;
- ejecución de `bash scripts/check_edge_functions.sh`.

Separar ambos jobs permite distinguir de inmediato:

- regresión funcional/contractual Python;
- regresión de compilación/runtime Edge.

Ambos deben estar verdes antes de merge.

## Por qué `deno check`

El objetivo inmediato es cubrir exactamente la clase de defecto que escapó en v0.50: errores de parseo/sintaxis y errores TypeScript que Python no puede detectar.

`deno check` ofrece una barrera local, determinista respecto a la versión de Deno fijada y sin necesidad de desplegar contra producción.

No pretende sustituir el bundle real de Supabase durante release. La política pasa a ser:

`pytest PASS + deno check PASS` antes del merge, y bundle/deploy real cuando una release modifique funciones productivas.

## Fail-closed de inventario

El gate compara:

- cantidad de directorios inmediatos bajo `supabase/functions`;
- cantidad de `index.ts` descubiertos.

Si un futuro desarrollador crea un nuevo directorio Edge y olvida su entrypoint, CI falla. Si crea un entrypoint nuevo en un directorio, queda automáticamente incluido sin editar una allowlist.

## Seguridad

El job GitHub declara `permissions: contents: read`.

No recibe:

- `SUPABASE_SERVICE_ROLE_KEY`;
- tokens de dashboard;
- claves de producción;
- credenciales de mercado.

El script tampoco contiene comandos de deploy o migración.

Por tanto el gate no puede alterar producción.

## Criterios de aceptación

1. CI contiene un job `edge-build` separado.
2. Deno está fijado en 2.9.5.
3. `setup-deno` está pinneado por commit.
4. El gate descubre funciones dinámicamente.
5. Falla si no existen entrypoints.
6. Falla si el número de directorios y entrypoints diverge.
7. Ejecuta `deno check` sobre cada función.
8. Un fallo identifica la función responsable.
9. El job no posee secretos ni autoridad de producción.
10. La suite Python sigue ejecutándose independientemente.
11. Versión de paquete y runtime = `0.51.0`.
12. Merge sintético exige PASS de ambos jobs.
13. No hay migración ni cambio de negocio en esta release.

## Siguiente endurecimiento posible

Una fase futura puede aproximar todavía más el gate al bundler concreto de Supabase, siempre que pueda hacerse sin credenciales productivas ni efectos laterales. v0.51 resuelve primero la brecha crítica y reproducible: código Edge no parseable/type-checkable ya no puede fusionarse silenciosamente.
