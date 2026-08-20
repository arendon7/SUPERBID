# SUPERBID Deal Intelligence v0.15

Motor de inteligencia para compra y reventa de vehículos subastados en Superbid Colombia.

## Qué resuelve

- descubre automáticamente subastas abiertas de Autos y Camiones;
- monitorea puja actual, número de pujas, cierre y estado;
- descarga/referencia anexos públicos y detecta **peritajes** automáticamente;
- construye histórico sin confundir **última puja observada** con **adjudicación confirmada**;
- cruza Fasecolda y comparables de mercado;
- calcula reventa conservadora, costo total, puja máxima, utilidad, ROI y score;
- entrega dashboard y exportaciones CSV/XLSX.

## v0.15 — collector 24/7 dentro de Supabase

La operación normal ya no necesita un servidor persistente ni Chromium. PostgreSQL/Supabase consulta directamente los endpoints públicos de Superbid mediante la extensión `http` y programa el trabajo con `pg_cron`.

Arquitectura:

`Superbid public HTTP -> Supabase pg_cron -> PostgreSQL histórico -> valoración/dashboard`

Playwright/Chromium queda como fallback para validación de cambios del frontend y casos especiales.

### Jobs

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
- [`SECURITY.md`](SECURITY.md)

## Principio de seguridad de datos

La herramienta solo recolecta datos públicamente accesibles o autorizados. No evade CAPTCHA, autenticación, controles de acceso ni rate limits.
