# Production

Supabase project: `superbid-deal-intelligence` (`bxsfxydhuaqlkfoicbaz`, `sa-east-1`).

## Required secrets
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPERBID_ADMIN_TOKEN`
- `SUPERBID_DASHBOARD_TOKEN`
- `MELI_ACCESS_TOKEN` when Mercado Libre comparables are enabled

## Non-secret environment
- `SUPABASE_URL=https://bxsfxydhuaqlkfoicbaz.supabase.co`
- `SUPERBID_DB=/data/superbid.db`
- `SUPERBID_SYNC_INTERVAL=300`
- `SUPERBID_DISCOVERY_URLS=<public listing/search pages>`

## Processes
`supervisord` runs:
1. FastAPI / dashboard;
2. Playwright collector worker;
3. Supabase sync worker.

## Health
- `/health`
- `/health/operational`
- `/operations/status`
- `/sync/status`
