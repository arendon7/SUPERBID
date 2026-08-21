# SUPERBID Deal Intelligence v0.19

Motor de inteligencia para compra y reventa de vehículos subastados en Superbid Colombia.

## Qué resuelve

- descubre automáticamente subastas abiertas de Autos y Camiones;
- monitorea puja actual, número de pujas, cierre y estado;
- descarga/referencia anexos públicos y detecta **peritajes** automáticamente;
- construye histórico sin confundir **última puja observada** con **adjudicación confirmada**;
- cruza Fasecolda y comparables de mercado;
- calcula reventa conservadora, costo total, puja máxima, utilidad, ROI y score;
- prioriza qué lotes revisar primero mientras mercado/costos estén pendientes;
- entrega dashboard y exportaciones CSV/XLSX.

## v0.19 — cola de revisión priorizada

`lot_review_queue_current` ordena dónde invertir primero el tiempo de análisis sin convertir señales preliminares en una recomendación de compra.

El `review_score` combina:
- headroom preliminar vs. Fasecolda: hasta 40 puntos;
- peritaje disponible: 25;
- urgencia de cierre: hasta 20;
- actividad de pujas: hasta 10;
- comisión pública: hasta 5.

Estados:
- `CLOSED_OR_PAST`
- `BLOCKED_VALUATION`
- `NO_HEADROOM`
- `REVIEW_NOW`
- `REVIEW_SOON`
- `WATCH`

**`REVIEW_NOW` significa revisar el peritaje/costos/mercado ahora; nunca significa `COMPRAR`.** La vista conserva `needs_market_validation=true` y `needs_cost_review=true`.

## v0.18 — Mercado Libre/TuCarro + validación de mercado

La integración de comparables usa la API oficial de Mercado Libre Colombia (`MCO`) mediante OAuth. No hay fallback de scraping para evadir autenticación.

Seguridad OAuth:
- callback: `https://bxsfxydhuaqlkfoicbaz.supabase.co/functions/v1/meli-oauth`;
- PKCE S256;
- `state` hasheado, de un solo uso y con expiración de 10 minutos;
- `client_secret`, access token y refresh token cifrados en Supabase Vault;
- refresh token rotatorio;
- el callback no devuelve tokens al navegador.

Mientras la aplicación Mercado Libre no esté autorizada, `market_connections.status=APP_REQUIRED` y la cola queda `AUTH_REQUIRED`; el cron no ejecuta búsquedas reales.

Cada comparable debe pasar año exacto, identidad marca/línea y score mínimo de similitud. Se almacenan ID público, URL, precio pedido, marca/modelo/versión, año, km, ciudad, tipo de vendedor estructurado y match score; no se guardan contactos ni identidad personal.

`market_valuations` calcula mediana, P25, P75, dispersión, confianza y venta rápida (`P25 × 95%`). `READY` exige al menos 3 comparables compatibles.

Reventa conservadora validada:

`min(venta rápida de mercado, Fasecolda × 95%)`

`lot_cost_overrides` permite registrar costos específicos del vehículo. `lot_opportunity_market_validated` solo habilita `market_final_buy_recommendation_available=true` con Fasecolda `HIGH`, comisión, Mercado Libre `READY`, costos completos/revisados y puja actual.

## v0.17 — oportunidad preliminar segura

`lot_opportunity_preliminary` combina puja, comisión, IVA, Fasecolda `HIGH`, utilidad objetivo, techo antes de costos, comparables/peritajes y estado. El perfil `PRELIMINARY_FASECOLDA` usa IVA 19%, utilidad objetivo 12%, utilidad mínima COP 3.000.000 y reventa preliminar de 90% de Fasecolda. Los costos desconocidos permanecen `NULL`, por lo que esta etapa nunca emite recomendación final.

## v0.16 — Fasecolda actual + histórico

La Guía de Valores de Fasecolda se consulta mediante el backend público usado por su aplicación web. El flujo identifica códigos candidatos, ficha por versión/año y serie mensual por código homologado.

Estados de matching: `HIGH`, `MEDIUM`, `AMBIGUOUS`, `UNMATCHED`.

La compuerta de identidad de línea se ejecuta antes del fuzzy matching y evita falsos positivos como `Traverse -> Tracker`, `C4 -> C3` o `NHR -> NQR`.

Cron Fasecolda: cada 5 minutos, máximo 6 lotes por ciclo; lotes nuevos o modificados vuelven automáticamente a cola.

## v0.15 — collector 24/7 dentro de Supabase

La operación normal no necesita un servidor persistente ni Chromium. PostgreSQL/Supabase consulta directamente los endpoints públicos de Superbid mediante `http` y programa trabajo con `pg_cron`.

Arquitectura:

`Superbid public HTTP -> Supabase pg_cron -> histórico -> Fasecolda -> Mercado Libre -> valoración`

Playwright/Chromium queda como fallback para validación de cambios del frontend y casos especiales.

Jobs Superbid:
- `superbid-discovery-v15`: cada 15 minutos;
- `superbid-refresh-v15`: cada 1 minuto, hasta 40 lotes por ciclo.

Cadencia adaptativa: >24h 4h; 24h–2h 30m; 2h–15m 5m; últimos 15m 1m; post-cierre seguimiento de extensiones/After Market/venta explícita.

## Peritajes y anexos

`product.attachments` se clasifica así:
- `PERITAJE`, `INSPECCION`, `AVALUO` -> `PERITAJE`;
- otros PDF -> `DOCUMENTO`;
- otros archivos -> `ANEXO`;
- fotos no se guardan como anexos.

## Calidad y seguridad de datos

Nunca se promueve una puja observada a venta confirmada sin señal explícita `offerStatus.sold=true`.

Fasecolda es una referencia comercial, no un precio de transacción. Los precios Mercado Libre son precios pedidos, no precios vendidos.

No se almacena `reservedPrice`, identidad de pujadores, cookies, tokens de mercado en tablas analíticas, sesiones ni filtros opacos.

RLS permanece activo y `anon/authenticated` no tienen acceso directo a tablas ni funciones operativas.

## Alcance vehicular

Taxonomía pública Colombia:
- `10000` -> Autos;
- `10022` -> Camiones;
- `10012` -> Motos, fuera del alcance por defecto.

Las ofertas `Shopping`/venta directa se excluyen.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[browser,dev]"
playwright install chromium
pytest -q
```

## Producción

Supabase central: `bxsfxydhuaqlkfoicbaz` (`sa-east-1`).

Consulte:
- [`docs/PRODUCTION.md`](docs/PRODUCTION.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_QUALITY.md`](docs/DATA_QUALITY.md)
- [`docs/V015_SUPABASE_CRON.md`](docs/V015_SUPABASE_CRON.md)
- [`docs/V016_FASECOLDA_MATCHING.md`](docs/V016_FASECOLDA_MATCHING.md)
- [`docs/V017_PRELIMINARY_OPPORTUNITY.md`](docs/V017_PRELIMINARY_OPPORTUNITY.md)
- [`docs/V018_MARKET_COMPARABLES.md`](docs/V018_MARKET_COMPARABLES.md)
- [`docs/V019_REVIEW_QUEUE.md`](docs/V019_REVIEW_QUEUE.md)
- [`SECURITY.md`](SECURITY.md)

## Principio de seguridad de datos

La herramienta solo recolecta datos públicamente accesibles o autorizados. No evade CAPTCHA, autenticación, controles de acceso ni rate limits.
