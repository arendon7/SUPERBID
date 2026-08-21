# SUPERBID Deal Intelligence v0.18

Motor de inteligencia para compra y reventa de vehículos subastados en Superbid Colombia.

## Qué resuelve

- descubre automáticamente subastas abiertas de Autos y Camiones;
- monitorea puja actual, número de pujas, cierre y estado;
- descarga/referencia anexos públicos y detecta **peritajes** automáticamente;
- construye histórico sin confundir **última puja observada** con **adjudicación confirmada**;
- cruza Fasecolda y comparables de mercado;
- calcula reventa conservadora, costo total, puja máxima, utilidad, ROI y score;
- entrega dashboard y exportaciones CSV/XLSX.

## v0.18 — Mercado Libre/TuCarro + validación de mercado

La integración de comparables usa la API oficial de Mercado Libre Colombia (`MCO`) mediante OAuth. No hay fallback de scraping para evadir autenticación.

Seguridad OAuth:

- callback: `https://bxsfxydhuaqlkfoicbaz.supabase.co/functions/v1/meli-oauth`;
- PKCE S256;
- `state` hasheado, de un solo uso y con expiración de 10 minutos;
- `client_secret`, access token y refresh token se guardan cifrados en Supabase Vault;
- el refresh token rota automáticamente;
- el callback no devuelve tokens al navegador.

Mientras la aplicación Mercado Libre no esté autorizada, `market_connections.status=APP_REQUIRED` y la cola queda `AUTH_REQUIRED`; el cron no ejecuta búsquedas reales.

### Comparables

Cada resultado debe pasar:

1. año exacto;
2. identidad marca/línea mediante `fasecolda_line_compatible`;
3. score mínimo de similitud de versión/título.

Se almacenan únicamente:
- ID público y URL del anuncio;
- precio pedido;
- marca/modelo/versión;
- año;
- kilometraje;
- ciudad;
- tipo de vendedor cuando la API lo expone estructuradamente;
- score de matching.

No se guardan contactos, identidad personal del vendedor, teléfonos ni correos.

`market_valuations` calcula mediana, P25, P75, dispersión, confianza y venta rápida (`P25 × 95%`). `READY` exige al menos 3 comparables compatibles.

La reventa conservadora validada se calcula como:

`min(venta rápida de mercado, Fasecolda × 95%)`

### Costos por lote y decisión final

`lot_cost_overrides` permite registrar costos específicos del vehículo: traspaso, impuestos/SOAT, transporte, reparación, detailing, financiación, administración y contingencia.

`lot_opportunity_market_validated` solo habilita `market_final_buy_recommendation_available=true` cuando existen:

- Fasecolda `HIGH`;
- comisión pública;
- Mercado Libre `READY` con al menos 3 comparables;
- todos los costos completos;
- costos revisados (`reviewed_at`);
- puja actual.

Estados finales posibles:
- `REVIEW_VALUATION`
- `REVIEW_COMMISSION`
- `MARKET_VALIDATION_PENDING`
- `CONFIGURE_COSTS`
- `NO_CURRENT_BID`
- `NO_PUJAR`
- `VIGILAR`
- `RIESGO`
- `COMPRAR`

## v0.17 — oportunidad preliminar segura

La vista `lot_opportunity_preliminary` combina por lote:

- puja actual;
- comisión pública de Superbid;
- IVA sobre comisión;
- Fasecolda `HIGH` actual e histórico;
- haircut conservador sobre Fasecolda;
- utilidad objetivo;
- techo antes de costos fijos;
- costos fijos configurados/no configurados;
- comparables disponibles;
- peritajes;
- estado de oportunidad.

El perfil inicial `PRELIMINARY_FASECOLDA` usa IVA 19%, utilidad objetivo 12%, utilidad mínima COP 3.000.000 y referencia de reventa 90% de Fasecolda. Los costos desconocidos permanecen `NULL`; por eso v0.17 nunca emite recomendación final.

## v0.16 — Fasecolda actual + histórico

La Guía de Valores de Fasecolda se consulta mediante el backend público usado por su aplicación web. El flujo identifica códigos candidatos, ficha por versión/año y serie mensual por código homologado.

Estados de matching:
- `HIGH`
- `MEDIUM`
- `AMBIGUOUS`
- `UNMATCHED`

La compuerta de identidad de línea se ejecuta antes del fuzzy matching y evita falsos positivos como `Traverse -> Tracker`, `C4 -> C3` o `NHR -> NQR`.

Cron Fasecolda:
- cada 5 minutos;
- máximo 6 lotes por ciclo;
- lotes nuevos o modificados vuelven automáticamente a cola.

## v0.15 — collector 24/7 dentro de Supabase

La operación normal no necesita un servidor persistente ni Chromium. PostgreSQL/Supabase consulta directamente los endpoints públicos de Superbid mediante `http` y programa trabajo con `pg_cron`.

Arquitectura:

`Superbid public HTTP -> Supabase pg_cron -> histórico -> Fasecolda -> Mercado Libre -> valoración`

Playwright/Chromium queda como fallback para validación de cambios del frontend y casos especiales.

Jobs Superbid:
- `superbid-discovery-v15`: cada 15 minutos;
- `superbid-refresh-v15`: cada 1 minuto, hasta 40 lotes por ciclo.

Cadencia adaptativa por lote:
- >24 h: 4 h;
- 24 h–2 h: 30 min;
- 2 h–15 min: 5 min;
- últimos 15 min: 1 min;
- post-cierre: seguimiento para extensiones, After Market y confirmación explícita.

## Peritajes y anexos

Superbid expone documentos públicos en `product.attachments`.

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
- [`docs/V013_DIRECT_PUBLIC_API.md`](docs/V013_DIRECT_PUBLIC_API.md)
- [`docs/V015_SUPABASE_CRON.md`](docs/V015_SUPABASE_CRON.md)
- [`docs/V016_FASECOLDA_MATCHING.md`](docs/V016_FASECOLDA_MATCHING.md)
- [`docs/V017_PRELIMINARY_OPPORTUNITY.md`](docs/V017_PRELIMINARY_OPPORTUNITY.md)
- [`docs/V018_MARKET_COMPARABLES.md`](docs/V018_MARKET_COMPARABLES.md)
- [`SECURITY.md`](SECURITY.md)

## Principio de seguridad de datos

La herramienta solo recolecta datos públicamente accesibles o autorizados. No evade CAPTCHA, autenticación, controles de acceso ni rate limits.
