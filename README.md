# SUPERBID Deal Intelligence v0.17

Motor de inteligencia para compra y reventa de vehículos subastados en Superbid Colombia.

## Qué resuelve

- descubre automáticamente subastas abiertas de Autos y Camiones;
- monitorea puja actual, número de pujas, cierre y estado;
- descarga/referencia anexos públicos y detecta **peritajes** automáticamente;
- construye histórico sin confundir **última puja observada** con **adjudicación confirmada**;
- cruza Fasecolda y comparables de mercado;
- calcula reventa conservadora, costo total, puja máxima, utilidad, ROI y score;
- entrega dashboard y exportaciones CSV/XLSX.

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

El perfil inicial `PRELIMINARY_FASECOLDA` usa:

- IVA sobre comisión: 19%;
- utilidad objetivo: 12% del valor preliminar;
- utilidad mínima: COP 3.000.000;
- referencia de reventa: 90% de Fasecolda.

Los costos de traspaso, impuestos/SOAT, transporte, reparación, alistamiento, financiación, administración y contingencia quedan `NULL` hasta ser configurados. Por tanto, v0.17 **no emite recomendación final de compra**.

Estados principales:

- `REVIEW_VALUATION`
- `REVIEW_COMMISSION`
- `NO_CURRENT_BID`
- `CONFIGURE_COSTS`
- `MARKET_VALIDATION_PENDING`
- `PRELIMINARY_OVER_CEILING`
- `PRELIMINARY_WITHIN_CEILING`

En todos los casos:

`final_buy_recommendation_available = false`

## v0.16 — Fasecolda actual + histórico

La Guía de Valores de Fasecolda se consulta mediante el backend público usado por su propia aplicación web:

`https://fasecoldaback.quantil.co/api/`

Flujo:

1. búsqueda textual → códigos candidatos;
2. ficha por código → marca/línea/versión/año/valor;
3. histórico por código homologado → serie mensual;
4. matching conservador contra el título Superbid.

Estados de matching:

- `HIGH`: referencia suficientemente clara para usar como referencia principal;
- `MEDIUM`: probable, pero requiere revisión si se quiere tratar como versión exacta;
- `AMBIGUOUS`: varias versiones plausibles; se conserva rango min/mediana/max;
- `UNMATCHED`: no hay referencia defendible.

La compuerta de identidad de línea se ejecuta antes del fuzzy matching. Evita errores como `Traverse -> Tracker`, `C4 -> C3` o `NHR -> NQR`.

Cron Fasecolda:

- cada **5 minutos**;
- máximo **6 lotes** por ciclo;
- lotes nuevos o con título/año modificado vuelven automáticamente a cola.

Para matches `HIGH` se almacena la serie en `fasecolda_value_history`.

La vista `lot_intelligence_current` unifica por lote:

- puja actual;
- número de pujas;
- cierre;
- estado Superbid;
- Fasecolda actual;
- Fasecolda ~12 meses atrás y variación;
- rango de candidatos;
- confianza;
- peritajes y enlaces.

## v0.15 — collector 24/7 dentro de Supabase

La operación normal no necesita un servidor persistente ni Chromium. PostgreSQL/Supabase consulta directamente los endpoints públicos de Superbid mediante la extensión `http` y programa el trabajo con `pg_cron`.

Arquitectura:

`Superbid public HTTP -> Supabase pg_cron -> PostgreSQL histórico -> Fasecolda -> valoración/dashboard`

Playwright/Chromium queda como fallback para validación de cambios del frontend y casos especiales.

### Jobs Superbid

- `superbid-discovery-v15`: cada **15 minutos**;
- `superbid-refresh-v15`: cada **1 minuto**, hasta 40 lotes por ciclo.

### Cadencia adaptativa por lote

- más de 24 h al cierre: 4 h;
- 24 h–2 h: 30 min;
- 2 h–15 min: 5 min;
- últimos 15 min: 1 min;
- después del cierre: seguimiento progresivo para capturar extensiones, After Market y eventual confirmación explícita.

El cierre canónico usa `endDateTime` (epoch milisegundos). `endDate` se conserva solo como texto de evidencia.

## Peritajes y anexos

Superbid expone documentos públicos en `product.attachments`.

- nombres con `PERITAJE`, `INSPECCION` o `AVALUO` -> `PERITAJE`;
- otros PDF -> `DOCUMENTO`;
- otros archivos -> `ANEXO`;
- fotos de `galleryJson` no se guardan como anexos.

## Calidad de datos

Nunca se promueve una puja observada a venta confirmada sin señal explícita `offerStatus.sold=true`.

Estados principales:

- `ACTIVE`
- `CLOSED_OBSERVED`
- `AFTER_MARKET`
- `SOLD_CONFIRMED`
- `WITHDRAWN`
- `UNKNOWN`

Fasecolda es una **referencia comercial** y no se trata como precio de transacción.

No se almacena `reservedPrice`, identidad de pujadores, cookies, tokens, sesiones ni filtros opacos.

## Alcance vehicular

Taxonomía pública Colombia:

- `10000` -> Autos;
- `10022` -> Camiones;
- `10012` -> Motos, actualmente fuera del alcance por defecto.

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

Supabase central: `bxsfxydhuaqlkfoicbaz` (`sa-east-1`). RLS permanece activo y `anon/authenticated` no tienen acceso directo a las tablas ni a las funciones operativas.

Consulte:
- [`docs/PRODUCTION.md`](docs/PRODUCTION.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_QUALITY.md`](docs/DATA_QUALITY.md)
- [`docs/V013_DIRECT_PUBLIC_API.md`](docs/V013_DIRECT_PUBLIC_API.md)
- [`docs/V015_SUPABASE_CRON.md`](docs/V015_SUPABASE_CRON.md)
- [`docs/V016_FASECOLDA_MATCHING.md`](docs/V016_FASECOLDA_MATCHING.md)
- [`docs/V017_PRELIMINARY_OPPORTUNITY.md`](docs/V017_PRELIMINARY_OPPORTUNITY.md)
- [`SECURITY.md`](SECURITY.md)

## Principio de seguridad de datos

La herramienta solo recolecta datos públicamente accesibles o autorizados. No evade CAPTCHA, autenticación, controles de acceso ni rate limits.
