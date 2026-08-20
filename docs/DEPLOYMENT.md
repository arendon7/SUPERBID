# Despliegue v0.3

## Local con Docker

```bash
mkdir -p data
cp data/watchlist.txt data/watchlist.txt
docker compose up --build
```

API:
- `GET /health`
- `GET /lots`
- `GET /lots/{external_lot_id}`
- `GET /analytics/summary`
- `GET /export/lots.csv`

Swagger:
- `/docs`

## Arquitectura

`worker`:
- abre URLs públicas de watchlist;
- observa JSON/XHR;
- normaliza lotes;
- guarda snapshots.

`api`:
- no realiza scraping;
- expone únicamente la base capturada.

Ambos comparten `/data/superbid.db`.

## Producción

Para producción conviene reemplazar SQLite por PostgreSQL/Supabase cuando:
- existan varios workers;
- queramos dashboard multiusuario;
- el histórico supere cientos de miles de snapshots.

No desplegar el worker en plataformas serverless de corta duración.
Debe vivir como proceso/worker persistente con Chromium disponible.
