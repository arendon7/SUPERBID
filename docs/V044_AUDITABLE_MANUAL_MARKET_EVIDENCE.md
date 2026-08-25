# v0.44 — Evidencia manual auditable de mercado

## Diagnóstico productivo

Al cerrar v0.43 se auditó `dashboard_economic_readiness_current` en producción:

- 292 lotes activos estaban `BLOCKED`;
- 111 estaban cerrados;
- 198 tenían `next_action = REVIEW_VALUATION`;
- 65 `REVIEW_PERITAJE`;
- 21 `VALIDATE_MARKET`;
- 8 `REVIEW_COMMISSION`.

Al mirar todos los blockers, no solo el primero, los **292 lotes activos** tenían simultáneamente:

- `MARKET_NOT_VALIDATED`;
- `LOT_COSTS_MISSING`;
- `LOT_COSTS_INCOMPLETE`;
- `LOT_COSTS_NOT_REVIEWED`.

El pipeline automático de mercado estaba técnicamente programado cada 10 minutos, pero la cola completa tenía 401 registros `AUTH_REQUIRED`, sin `last_run_at` ni `last_success_at`, porque `MERCADOLIBRE_MCO` seguía `APP_REQUIRED`.

v0.44 elimina ese single point of failure sin fingir que una fuente manual es Mercado Libre.

## Principio

Guardrails:

`MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION`

`MARKET_REVIEW_NOT_BUY_SIGNAL`

Una persona puede aportar evidencia real de mercado y revisarla. SUPERBID conserva la procedencia y puede usarla como **evidencia de mercado**, pero esa acción:

- no crea Fasecolda HIGH;
- no cambia costos;
- no rellena comisión;
- no cambia la puja actual;
- no fuerza `COMPRAR`;
- no escribe directamente `max_bid`, ROI o `final_decision`.

El motor económico existente sigue siendo quien combina todas las capas.

## Modelo de evidencia

### `market_manual_evidence_sets`

Cada guardado crea un set inmutable nuevo. No se edita evidencia histórica.

Estados:

- `DRAFT`: evidencia incompleta/no aprobada;
- `REVIEWED`: evidencia humana suficiente y explícitamente revisada.

Un set `REVIEWED` requiere:

- mínimo 3 comparables;
- máximo 20;
- URL `https://` única por comparable;
- precio COP dentro de rango válido;
- año exactamente igual al año del lote;
- título de la publicación;
- nota de revisión de al menos 10 caracteres.

Se conserva un fingerprint material del set.

### `market_manual_evidence_items`

Guarda cada comparable por separado:

- URL;
- título;
- precio publicado;
- año;
- ciudad;
- timestamp de observación;
- nota opcional.

No se interpreta precio publicado como precio transado.

## Métricas conservadoras

Al revisar el set se calculan:

- mediana;
- P25;
- P75;
- quick-sale = P25 × 95%;
- dispersión;
- confianza por número de comparables y dispersión.

La regla coincide conceptualmente con el motor de mercado existente y mantiene el sesgo conservador.

## Fuente efectiva

`market_valuation_effective_current` combina dos orígenes explícitos:

- `MERCADOLIBRE_PIPELINE`;
- `MANUAL_REVIEWED`.

`MERCADOLIBRE_PIPELINE` describe el origen técnico de filas de `market_valuations` sin afirmar que la conexión esté actualmente autenticada; el estado vivo continúa en `market_connections`.

La vista prioriza evidencia `READY`; entre evidencias READY usa la más reciente y conserva `evidence_origin`.

Un DRAFT nunca entra a la vista manual efectiva.

`lot_market_intelligence_current` sigue exponiendo, en el mismo orden pre-v0.44:

- `market_status`;
- número de comparables;
- P25;
- quick-sale;
- confianza;
- `market_validation_available`.

Y añade **al final** provenance:

- `market_validation_source`;
- `market_evidence_origin`;
- `market_evidence_set_id`;
- `market_evidence_fingerprint`;
- `market_evidence_observed_at`.

Esto preserva las 67 columnas preexistentes y evita romper vistas dependientes por cambio de posición.

La reventa conservadora continúa limitada por Fasecolda cuando ambas evidencias existen:

`least(quick_sale_market, fasecolda_current × 95%)`.

## RPC privada

`dashboard_save_manual_market_evidence(...)`

- solo `service_role`;
- valida nuevamente todos los datos en PostgreSQL;
- cada llamada crea un set nuevo;
- `p_mark_reviewed=true` exige >=3 comparables y nota;
- devuelve métricas del set, `buy_signal=false` y el guardrail.

El navegador nunca recibe `service_role`.

## Dashboard privado

Edge Function:

`superbid-market-review-dashboard`

Ruta:

`/functions/v1/superbid-market-review-dashboard`

La interfaz:

- usa `dashboard_token_valid` y cookie `HttpOnly; Secure; SameSite=Strict`;
- lista lotes bloqueados por `MARKET_NOT_VALIDATED`;
- prioriza menos blockers, mayor review score y cierre;
- muestra explícitamente `model_year` del lote;
- lee el estado vivo de `market_connections` para Mercado Libre, sin hardcodear `APP_REQUIRED`;
- permite guardar DRAFT o REVIEWED;
- acepta una línea por comparable:

`URL | PRECIO_COP | AÑO | TÍTULO | CIUDAD`

- muestra histórico de sets;
- no ejecuta matching Fasecolda;
- no modifica costos;
- no calcula decisiones en el HTML.

## Mercado Libre

v0.44 **no elimina** el pipeline OAuth de Mercado Libre. Cuando exista una aplicación autorizada, `market_valuations` volverá a producir evidencia por el pipeline automático y competirá en la vista efectiva según status y vigencia.

La evidencia manual es un camino auditable de continuidad operacional, no un bypass opaco.

## Gate de despliegue

Antes de producción se exige:

- CI completo verde sobre el HEAD exacto;
- `behind_by = 0` contra `main`;
- conservación del orden de las 67 columnas productivas actuales de `lot_market_intelligence_current`;
- nuevas columnas de provenance agregadas únicamente al final;
- migración y Edge Function desplegadas solo después del merge;
- verificación posterior de esquema y semántica de readiness.

## Certificación de código previa al merge

Candidato certificado:

`2e852d9a48e790aad68e9d1397410b1fd4244bbd`

- Python 3.12;
- suite completa: `242/242 PASS`;
- `behind_by = 0` contra `main` en el momento de certificación;
- diff acotado a seis archivos de v0.44;
- esquema productivo inspeccionado: 67 columnas existentes en `lot_market_intelligence_current`, preservadas en orden antes de las cinco nuevas columnas de provenance.
