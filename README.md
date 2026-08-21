# SUPERBID Deal Intelligence v0.24

Motor de inteligencia para compra y reventa de vehículos subastados en Superbid Colombia.

## Estado actual

- discovery de Autos/Camiones por HTTP directo;
- monitoreo 24/7 dentro de Supabase con `pg_cron`;
- puja, cierre, número de pujas y comisión pública;
- detección automática de peritajes/anexos;
- histórico con proveniencia estricta;
- Fasecolda actual + serie histórica + matching conservador;
- cola priorizada `REVIEW_NOW / REVIEW_SOON / WATCH`;
- OAuth Mercado Libre/TuCarro preparado, actualmente `APP_REQUIRED`;
- motor preliminar y motor final market-validated;
- dashboard central privado sobre Supabase;
- captura y revisión auditable de costos específicos por lote;
- histórico central descargable con `SALE_CONFIRMED / CLOSING_OBSERVED / NO_FINAL_VALUE`;
- eventos observados de cambio de precio/contador de pujas, sin presentarlos como lances individuales;
- presión competitiva descriptiva basada en actividad observada y extensiones de cierre.

## v0.24 — presión competitiva observada

`lot_bid_pressure_current` resume la actividad observada del lote y la clasifica como `HIGH`, `MEDIUM`, `LOW` o `NONE`.

Métricas principales:
- cambios y pujas observadas en 2h, 6h y 24h;
- incremento de precio en 2h/6h y acumulado;
- cambios y pujas acumuladas;
- último cambio observado;
- número de snapshots y horas de observación;
- extensiones de cierre detectadas cuando `closes_at` aumenta entre snapshots.

La señal está marcada como `OBSERVATIONAL_ONLY_NOT_BUY_SIGNAL`: describe intensidad competitiva, pero no modifica por sí sola el `review_score`, `review_state`, la puja máxima validada ni la decisión final.

API privada adicional: `GET /lots/{id}/bid-pressure`.

El detalle del dashboard muestra el nivel de presión y sus evidencias junto a la trayectoria observada.

## v0.23 — eventos observados de puja/precio

`lot_observed_bid_events` compara snapshots consecutivos y detecta cuándo cambió el precio mostrado, el contador de pujas o ambos.

Estados principales:
- `INITIAL_OBSERVATION`;
- `PRICE_AND_BID_COUNT_CHANGE`;
- `PRICE_CHANGE_OBSERVED`;
- `BID_COUNT_CHANGE_OBSERVED`.

Cada evento conserva precio anterior/actual, delta de precio, contador anterior/actual, delta de pujas, hora observada y estado vigente. Todos los registros derivados de snapshots llevan `is_individual_bid=false`.

Esto permite analizar presión competitiva y aceleración de precio sin inventar una secuencia de lances que la fuente pública no enumera. El detalle del lote muestra esta trayectoria en una tabla separada del histórico individual de lances.

API privada adicional: `GET /lots/{id}/observed-bid-events`.

## v0.22 — inteligencia histórica central

El histórico distingue obligatoriamente:
- `SALE_CONFIRMED`: venta/adjudicación explícitamente confirmada;
- `CLOSING_OBSERVED`: cierre observado sin prueba de venta;
- `NO_FINAL_VALUE`: no existe un valor final defendible.

`NO_FINAL_VALUE` nunca se rellena con la última puja. El timeline por lote incluye snapshots, serie Fasecolda, proveniencia, revisiones de costos y lances individuales únicamente cuando exista una fuente pública que realmente los enumere.

El dashboard incorpora búsqueda histórica y descarga `superbid_historico.csv`.

## v0.21 — revisión de costos por lote

Desde el detalle de cada lote se pueden registrar:
- traspaso;
- impuestos / SOAT;
- transporte;
- reparación;
- alistamiento;
- financiación;
- administración;
- contingencia.

El formulario permite guardar borradores incompletos y añadir notas/fuentes de soporte. Solo se puede marcar como `revisado` cuando los ocho costos estén completos.

Cualquier edición posterior invalida la revisión anterior (`reviewed_at = NULL`) hasta que se vuelva a marcar explícitamente como revisada. Cada guardado genera un snapshot en `lot_cost_review_history`, de modo que la construcción de la puja máxima sea auditable.

La función `dashboard_save_lot_costs(...)` solo puede ejecutarla `service_role`; `anon/authenticated` no tienen acceso directo.

## v0.20 — dashboard central

El dashboard dejó de depender de SQLite local. La fuente operativa es `dashboard_lot_current`, una vista backend-only que combina puja, cierre, comisión, Fasecolda, peritajes, review score, mercado, costos y resultados económicos cuando estén validados.

API privada: `superbid-read-api`.

Dashboard privado:
`https://bxsfxydhuaqlkfoicbaz.supabase.co/functions/v1/superbid-dashboard`

Características: server-rendered, login por POST, cookie `HttpOnly; Secure; SameSite=Strict`, filtros de prioridad, detalle por lote y acceso directo a peritajes públicos.

## v0.19 — cola de revisión

`lot_review_queue_current` prioriza dónde invertir primero el tiempo de análisis. `REVIEW_NOW` significa revisar costos/peritaje/mercado ahora; nunca significa `COMPRAR`.

## v0.18 — comparables Mercado Libre/TuCarro

La integración usa la API oficial `MCO` mediante OAuth + PKCE. Secretos/tokens están diseñados para vivir cifrados en Supabase Vault. Mientras no exista una aplicación autorizada, `market_connections.status=APP_REQUIRED` y no se hacen búsquedas ni se crean comparables ficticios.

`market_valuations` calcula mediana, P25, P75, dispersión, confianza y venta rápida. `READY` exige al menos 3 comparables compatibles. La decisión final también exige costos específicos del lote completos y revisados.

## v0.17 — oportunidad preliminar

Usa comisión pública, IVA sobre comisión, Fasecolda `HIGH`, haircut conservador y utilidad objetivo. Los costos desconocidos permanecen `NULL`; esta etapa nunca emite recomendación final.

## v0.16 — Fasecolda

Matching por marca/línea/versión/año con compuerta de identidad antes del fuzzy matching. Estados: `HIGH`, `MEDIUM`, `AMBIGUOUS`, `UNMATCHED`. Se conserva la serie histórica mensual para matches `HIGH`.

## v0.15 — operación 24/7

Supabase/PostgreSQL consulta los endpoints públicos de Superbid mediante `http` y agenda trabajo con `pg_cron`.

- discovery: cada 15 minutos;
- refresh: cada minuto, con cadencia adaptativa por cercanía al cierre;
- Playwright queda como fallback para validación/casos especiales.

## Calidad y seguridad

- nunca se equipara una puja observada con adjudicación confirmada;
- una venta exige señal explícita `offerStatus.sold=true`;
- un cambio entre snapshots no se presenta como lance individual;
- la presión competitiva es observacional, no una señal automática de compra;
- Fasecolda es referencia comercial, no precio de transacción;
- Mercado Libre aporta precios pedidos, no precios vendidos;
- no se almacena `reservedPrice`, identidad de pujadores, cookies ni filtros opacos;
- no se guardan contactos personales de vendedores de Mercado Libre;
- RLS está activo y `anon/authenticated` no tienen acceso directo a tablas ni funciones operativas;
- secretos de dashboard/OAuth no se guardan en GitHub.

## Alcance vehicular

- `10000` Autos;
- `10022` Camiones;
- `10012` Motos fuera del alcance por defecto;
- ofertas `Shopping` se excluyen.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[browser,dev]"
playwright install chromium
pytest -q
```

## Documentación

- [`docs/PRODUCTION.md`](docs/PRODUCTION.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_QUALITY.md`](docs/DATA_QUALITY.md)
- [`docs/V015_SUPABASE_CRON.md`](docs/V015_SUPABASE_CRON.md)
- [`docs/V016_FASECOLDA_MATCHING.md`](docs/V016_FASECOLDA_MATCHING.md)
- [`docs/V017_PRELIMINARY_OPPORTUNITY.md`](docs/V017_PRELIMINARY_OPPORTUNITY.md)
- [`docs/V018_MARKET_COMPARABLES.md`](docs/V018_MARKET_COMPARABLES.md)
- [`docs/V019_REVIEW_QUEUE.md`](docs/V019_REVIEW_QUEUE.md)
- [`docs/V020_CENTRAL_DASHBOARD.md`](docs/V020_CENTRAL_DASHBOARD.md)
- [`docs/V021_LOT_COST_REVIEW.md`](docs/V021_LOT_COST_REVIEW.md)
- [`docs/V022_HISTORICAL_INTELLIGENCE.md`](docs/V022_HISTORICAL_INTELLIGENCE.md)
- [`docs/V023_OBSERVED_BID_EVENTS.md`](docs/V023_OBSERVED_BID_EVENTS.md)
- [`docs/V024_BID_PRESSURE.md`](docs/V024_BID_PRESSURE.md)
- [`SECURITY.md`](SECURITY.md)

La herramienta solo recolecta datos públicamente accesibles o autorizados. No evade CAPTCHA, autenticación, controles de acceso ni rate limits.
