# v0.50.1 — Edge Bundle Hotfix

## Contexto

v0.50 fue certificada en GitHub con 314/314 pruebas PASS y fusionada a `main` como `8e5846c20ac35e0ffc205562ec299eb69f9f2d9c`.

La migración `20260826010000_peritaje_evidence_workbench_v50.sql` fue aplicada exitosamente en producción. PostgreSQL creó las tablas, RPC, trigger y vista previstos y no creó ninguna fila de evidencia automáticamente.

También se ejecutó un smoke transaccional real del RPC contra un lote con peritaje público usando `BEGIN ... ROLLBACK`. El RPC devolvió correctamente:

- `diagnosis_generated=false`;
- `buy_signal=false`;
- `cost_fields_modified=false`;
- `economic_fields_modified=false`;
- `overall_risk=NOT_EVALUABLE` para la dimensión de smoke;
- `not_evaluable_count=1`.

Después del rollback permanecieron 0 filas de evidencia y 0 revisiones canónicas.

## Fallo detectado en deploy

Al desplegar `superbid-peritaje-evidence-workbench`, el bundler de Supabase rechazó el source antes de publicar una versión de la función.

Causa:

- el HTML de la UI vive dentro de template literals TypeScript delimitados por backticks;
- dos fragmentos de copy usaban backticks Markdown crudos para `NOT_EVALUABLE` y `repair_cop`;
- esos caracteres terminaban prematuramente el template literal;
- pytest no detectó el problema porque la suite histórica inspeccionaba contratos de texto/Python y no compilaba las Edge Functions TypeScript.

El error fue capturado por el gate real de despliegue. Por tanto:

- el workbench v0.50 no fue publicado;
- Readiness v0.50 no fue desplegado;
- no hubo escrituras de negocio derivadas del intento fallido;
- la base de datos quedó con el contrato v0.50 aplicado y 0 evidencia ficticia.

## Corrección v0.50.1

La corrección sustituye los backticks de copy por HTML seguro dentro del template literal:

- `NOT_EVALUABLE` → `<strong>NOT_EVALUABLE</strong>`;
- `repair_cop` → `<code>repair_cop</code>`.

No cambia:

- el RPC;
- el modelo de datos;
- el trigger;
- las reglas de REVIEWED;
- el tratamiento de `NOT_EVALUABLE`;
- los límites de autoridad;
- el routing de Readiness.

Por tanto v0.50.1 no requiere una nueva migración.

## Regresión añadida

`test_edge_html_copy_does_not_break_template_literal_bundle` exige que el source no vuelva a contener los dos patrones de backticks que causaron el fallo real y que sí contenga sus equivalentes HTML seguros.

El versionado pasa a `0.50.1`.

## Lección de release engineering

Este incidente revela una brecha estructural: una suite Python completamente verde no garantiza que las Edge Functions TypeScript puedan ser parseadas/bundleadas por Supabase.

Después de cerrar v0.50.1 debe priorizarse un gate de build para todas las Edge Functions dentro de CI, idealmente mediante Deno/Supabase tooling, para que los errores sintácticos y de módulos se detecten antes del merge y no durante el deploy productivo.

## Criterios de aceptación

1. Suite histórica y regresiones v0.50/v0.50.1 PASS.
2. `pyproject.toml` y runtime package = `0.50.1`.
3. Branch 0 detrás de `main` antes del merge.
4. Workbench puede bundle/deploy realmente en Supabase.
5. Workbench queda ACTIVE con `verify_jwt=false` por su autenticación custom existente.
6. Solo después del workbench ACTIVE se despliega Readiness v0.50 routing.
7. Producción mantiene 0 evidencia/revisiones automáticas tras deploy.
8. No se fabrica evidencia para el UAT.
