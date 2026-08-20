# Validación de campo — 20 de agosto de 2026

Lotes públicos encontrados/indexados el mismo día:

- Mazda 3, modelo 2017 — ID 4972833 — Acopi/Yumbo/Cali.
- Kia Rio, modelo 2020 — ID 4973043 — Cali.
- Hino XZU640L HKMLN3, modelo 2018 — ID 4970123 — Girardota/Antioquia.
- Chevrolet Colorado Z71 4x4, modelo 2026 — ID 4963735 — Bucaramanga/Santander.

El rastreador textual externo recibe poco o ningún contenido útil de las páginas individuales.
La hipótesis técnica más fuerte es que el frontend hidrata los datos mediante JSON/XHR/fetch.

## Qué debe ejecutarse en una máquina con salida a Internet

```bash
pip install -e ".[browser,dev]"
playwright install chromium
superbid init-db --db superbid.db

superbid capture-json \
  "https://www.superbid.com.co/oferta/mazda-3-mod-2017-placa-2-ubic-acopi-yumbo-cali-4972833" \
  --db superbid.db \
  --seconds 15 \
  --dump-dir captures/4972833
```

La v0.2 no necesita conocer el endpoint de antemano: inspecciona respuestas JSON públicas,
reconoce objetos de oferta por su estructura y los convierte a observaciones normalizadas.

## Evidencia externa de estructura

Un scraper comercial de Superbid publicado en 2026 documenta campos como:

- id
- lot_number
- total_bidders
- total_bids
- end_date
- price
- winner_bid
- offer_status.sold
- offer_status.closed
- seller/store
- offer_detail.initial_bid_value
- offer_detail.current_max_bid
- auction

Esto sirve como contrato de reconocimiento, no como dependencia del proyecto.

## Decisión de privacidad/ética

Aunque ciertas respuestas puedan contener `reserved_price`, v0.2 deliberadamente NO almacena
el monto de reserva oculto. La herramienta se limitará a datos visibles/públicos necesarios
para inteligencia de compra y a indicadores de estado de la subasta.
