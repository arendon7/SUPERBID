# SUPERBID Deal Intelligence v0.13

Motor de inteligencia para compra y reventa de vehículos subastados en Superbid Colombia.

## Qué resuelve

- detecta y monitorea lotes públicos;
- registra puja actual, trayectoria de lances y fecha/hora de cierre cuando están disponibles;
- identifica anexos y peritajes públicos;
- construye histórico sin confundir **última puja** con **adjudicación confirmada**;
- cruza Fasecolda y comparables de mercado;
- calcula reventa conservadora, costo total, puja máxima, utilidad, ROI y score;
- entrega dashboard y exportaciones CSV/XLSX.

## v0.13 — validación HTTP directa

La v0.13 prueba si el endpoint público confirmado `offer-query.superbid.net/seo/offers/` puede refrescar un lote monitoreado sin Chromium, cookies del navegador, autenticación ni el parámetro opaco `filter`.

La sonda conserva únicamente parámetros públicos de enrutamiento como `portalId`, `locale`, `requestOrigin`, `timeZoneId` y `urlSeo`. Nunca persiste filtros opacos, tokens, cookies, reserva oculta ni identidad de pujadores.

Si la prueba real retorna el lote esperado, el monitoreo rutinario podrá pasar a HTTP directo y Chromium quedará como fallback para descubrimiento, anexos/peritajes y validación de cambios del frontend.

## Arquitectura

`Superbid -> HTTP directo / Playwright fallback -> SQLite buffer -> Supabase -> valoración -> dashboard`

Supabase central: `bxsfxydhuaqlkfoicbaz` (`sa-east-1`). La base está protegida con RLS y sin acceso directo para `anon/authenticated`.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[browser,dev]"
playwright install chromium
pytest -q
```

## Producción

Consulte:
- [`docs/PRODUCTION.md`](docs/PRODUCTION.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_QUALITY.md`](docs/DATA_QUALITY.md)
- [`docs/V013_DIRECT_PUBLIC_API.md`](docs/V013_DIRECT_PUBLIC_API.md)
- [`SECURITY.md`](SECURITY.md)

## Principio de seguridad de datos

La herramienta solo debe recolectar datos públicamente accesibles o autorizados. No debe evadir CAPTCHA, autenticación, controles de acceso ni rate limits, y no almacena identidades de pujadores ni precios de reserva ocultos.
