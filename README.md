# SUPERBID Deal Intelligence v0.11

Motor de inteligencia para compra y reventa de vehículos subastados en Superbid Colombia.

## Qué resuelve

- detecta y monitorea lotes públicos;
- registra puja actual, trayectoria de lances y fecha/hora de cierre cuando están disponibles;
- identifica anexos y peritajes públicos;
- construye histórico sin confundir **última puja** con **adjudicación confirmada**;
- cruza Fasecolda y comparables de mercado;
- calcula reventa conservadora, costo total, puja máxima, utilidad, ROI y score;
- entrega dashboard y exportaciones CSV/XLSX.

## v0.11 — descubrimiento paginado y Fasecolda central

- Las fuentes verificadas pueden registrarse como `paginated`; el collector conserva filtros existentes y recorre `pageNumber`/`pageSize` hasta la primera página vacía.
- No se inventa el slug colombiano de vehículos: `SUPERBID_DISCOVERY_PAGINATED_URLS` solo debe contener URLs públicas previamente verificadas.
- El parser acepta `winner_bid` numérico u objeto, registra `total_bidders` y comisión pública cuando exista, y sigue excluyendo `reserved_price` e identidad de pujadores.
- Fasecolda usa `record_key` determinístico y se replica idempotentemente a Supabase.

Ejemplo:

```bash
superbid add-discovery-source "URL_PUBLICA_VERIFICADA?searchType=opened" --type paginated
```

## Arquitectura

`Superbid -> Playwright/XHR -> SQLite buffer -> Supabase -> valoración -> dashboard`

Supabase central: `bxsfxydhuaqlkfoicbaz` (`sa-east-1`). La base está protegida con RLS y sin acceso directo para `anon/authenticated`.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[browser,dev]"
playwright install chromium

export SUPERBID_DB=superbid.db
export SUPERBID_ADMIN_TOKEN=dev-secret
uvicorn superbid_collector.api:app --reload
```

Dashboard: `http://127.0.0.1:8000/dashboard`

## Pruebas

```bash
pytest -q
```

La v0.11 tiene 37 pruebas unitarias aprobadas.

## Producción

Consulte:
- [`docs/PRODUCTION.md`](docs/PRODUCTION.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_QUALITY.md`](docs/DATA_QUALITY.md)
- [`SECURITY.md`](SECURITY.md)

## Principio de seguridad de datos

La herramienta solo debe recolectar datos públicamente accesibles o autorizados. No debe evadir CAPTCHA, autenticación, controles de acceso ni rate limits, y no almacena identidades de pujadores ni precios de reserva ocultos.
