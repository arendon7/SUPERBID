# SUPERBID Deal Intelligence v0.14

Motor de inteligencia para compra y reventa de vehículos subastados en Superbid Colombia.

## Qué resuelve

- descubre automáticamente inventario abierto de vehículos;
- monitorea cada lote con puja actual, trayectoria, cierre y estado;
- identifica anexos y peritajes públicos cuando existen;
- construye histórico sin confundir **última puja** con **adjudicación confirmada**;
- cruza Fasecolda y comparables de mercado;
- calcula reventa conservadora, costo total, puja máxima, utilidad, ROI y score;
- entrega dashboard y exportaciones CSV/XLSX.

## v0.14 — discovery HTTP directo confirmado

La plataforma pública de Colombia fue validada desde GitHub Actions con un cliente HTTP sin cookies, autenticación, `filter` opaco ni `fieldList`:

- `offer-query.superbid.net/offers/` → HTTP 200;
- inventario abierto observado en la validación: **352 lotes**;
- `offer-query.superbid.net/categories/` → HTTP 200;
- taxonomía pública útil para filtrar estructuradamente.

Categorías vehiculares confirmadas:

- `10000` → **Autos**;
- `10022` → **Camiones**;
- `10012` → **Motos** (opt-in, no incluida por defecto).

Por defecto el collector descubre **Autos + Camiones** (`10000,10022`).

## Arquitectura

`Superbid public HTTP -> discovery/monitoring -> SQLite buffer -> Supabase -> valoración -> dashboard`

Playwright/Chromium queda como fallback para cambios del contrato, inspección de anexos/peritajes y validación del frontend.

Supabase central: `bxsfxydhuaqlkfoicbaz` (`sa-east-1`). La base está protegida con RLS y sin acceso directo para `anon/authenticated`.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[browser,dev]"
playwright install chromium
pytest -q
```

## Variables principales

```bash
SUPERBID_DIRECT_HTTP_ENABLED=1
SUPERBID_DIRECT_DISCOVERY_ENABLED=1
SUPERBID_BROWSER_DISCOVERY_ALWAYS=0
SUPERBID_VEHICLE_CATEGORY_IDS=10000,10022
```

Para incluir motos: `SUPERBID_VEHICLE_CATEGORY_IDS=10000,10022,10012`.

## Producción

Consulte:
- [`docs/PRODUCTION.md`](docs/PRODUCTION.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_QUALITY.md`](docs/DATA_QUALITY.md)
- [`docs/V013_DIRECT_PUBLIC_API.md`](docs/V013_DIRECT_PUBLIC_API.md)
- [`SECURITY.md`](SECURITY.md)

## Principio de seguridad de datos

La herramienta solo recolecta datos públicamente accesibles o autorizados. No evade CAPTCHA, autenticación, controles de acceso ni rate limits, y no almacena identidades de pujadores ni precios de reserva ocultos.
