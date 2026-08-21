# SUPERBID Deal Intelligence v0.20

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
- dashboard central privado sobre Supabase.

## v0.20 — dashboard central

El dashboard dejó de depender de SQLite local. La fuente operativa es `dashboard_lot_current`, una vista backend-only que combina:

- puja actual y cierre;
- número de pujas;
- comisión pública;
- Fasecolda actual e histórico ~12 meses;
- peritajes;
- review score/state;
- comparables/venta rápida cuando Mercado Libre esté `READY`;
- costos revisados por lote;
- puja máxima, utilidad y ROI únicamente cuando la validación final esté disponible.

### API privada

Edge Function `superbid-read-api`:

- `/health`
- `/summary`
- `/review-queue`
- `/lots/{external_lot_id}`
- `/history`

Requiere una credencial de lectura almacenada en Supabase Vault. Nunca expone `service_role` al navegador.

### Dashboard privado

Edge Function `superbid-dashboard`:

`https://bxsfxydhuaqlkfoicbaz.supabase.co/functions/v1/superbid-dashboard`

Características:

- server-rendered, sin JavaScript cliente;
- login por POST;
- cookie `HttpOnly; Secure; SameSite=Strict`;
- filtros por prioridad;
- detalle por lote;
- acceso directo a peritajes públicos;
- indica explícitamente que `REVIEW_NOW` es prioridad de análisis, no una señal `COMPRAR`.

## v0.19 — cola de revisión

`lot_review_queue_current` prioriza dónde invertir primero el tiempo de análisis. El score combina headroom preliminar, peritaje, urgencia de cierre, actividad de pujas y comisión. Estados: `CLOSED_OR_PAST`, `BLOCKED_VALUATION`, `NO_HEADROOM`, `REVIEW_NOW`, `REVIEW_SOON`, `WATCH`.

## v0.18 — comparables Mercado Libre/TuCarro

La integración usa la API oficial `MCO` mediante OAuth + PKCE. `client_secret`, access token y refresh token están diseñados para vivir cifrados en Supabase Vault. Mientras no exista una aplicación autorizada, `market_connections.status=APP_REQUIRED` y no se hacen búsquedas ni se crean comparables ficticios.

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
- [`SECURITY.md`](SECURITY.md)

La herramienta solo recolecta datos públicamente accesibles o autorizados. No evade CAPTCHA, autenticación, controles de acceso ni rate limits.
