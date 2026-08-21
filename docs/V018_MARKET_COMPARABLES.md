# v0.18 — Mercado Libre/TuCarro comparables

## Objetivo
Validar el valor de reventa con anuncios clasificados reales antes de habilitar una recomendación final de compra.

## Fuente
La integración usa exclusivamente la API oficial de Mercado Libre Colombia (`MCO`) con OAuth. No existe fallback de scraping para evadir autenticación.

## OAuth
- callback: `https://bxsfxydhuaqlkfoicbaz.supabase.co/functions/v1/meli-oauth`;
- PKCE S256;
- `state` aleatorio, hasheado y de un solo uso;
- expiración de estado: 10 minutos;
- `client_secret`, access token y refresh token en Supabase Vault;
- el refresh token se reemplaza cuando Mercado Libre entrega uno nuevo;
- el callback no requiere JWT porque valida `state` + PKCE en la base y solo llama RPC con `service_role` interno.

Estados:
- `APP_REQUIRED`
- `AUTHORIZATION_REQUIRED`
- `READY`
- `TOKEN_EXPIRED`
- `ERROR`
- `DISABLED`

## Pipeline de comparables
`market_comparable_queue` contiene los lotes por analizar. El cron `market-comparables-v18` ejecuta hasta 4 lotes cada 10 minutos.

Mientras OAuth no esté `READY`, la cola queda en `AUTH_REQUIRED` y no se realizan búsquedas.

Para cada lote:
1. consulta autenticada `/sites/MCO/search`;
2. búsqueda por marca/línea/año;
3. año debe coincidir exactamente;
4. la línea debe pasar `fasecolda_line_compatible`;
5. se calcula similitud de título/versión;
6. solo se almacenan comparables compatibles.

Datos guardados:
- ID público del anuncio;
- URL;
- precio pedido;
- marca/modelo/versión;
- año;
- kilometraje;
- ciudad;
- tipo de vendedor cuando la API lo expone de forma estructurada;
- score de matching.

No se almacenan teléfonos, correo, dirección personal, identidad de usuario vendedor ni información de contacto.

## Valoración
`market_valuations` calcula:
- número de comparables;
- mediana;
- P25;
- P75;
- dispersión IQR/mediana;
- venta rápida preliminar = P25 × 95%;
- confianza según cantidad y dispersión.

`READY` exige al menos 3 comparables compatibles. Con menos evidencia se usa `LOW_EVIDENCE` y no se habilita decisión final.

## Reventa conservadora validada
Cuando Mercado Libre está `READY`, la referencia conservadora es:

`min(venta rápida mercado, Fasecolda × 95%)`

Esto evita que un conjunto de anuncios caros empuje la valoración por encima de la guía de referencia.

## Costos por lote
`lot_cost_overrides` permite registrar por vehículo:
- traspaso;
- impuestos/SOAT;
- transporte;
- reparación;
- detailing;
- financiación;
- tarifa administrativa;
- contingencia.

Una recomendación final requiere:
- Fasecolda `HIGH`;
- comisión pública;
- Mercado Libre `READY` con ≥3 comparables;
- todos los costos completos;
- costos revisados (`reviewed_at`);
- puja actual disponible.

## Estados finales
- `REVIEW_VALUATION`
- `REVIEW_COMMISSION`
- `MARKET_VALIDATION_PENDING`
- `CONFIGURE_COSTS`
- `NO_CURRENT_BID`
- `NO_PUJAR`
- `VIGILAR`
- `RIESGO`
- `COMPRAR`

`COMPRAR` no puede aparecer antes de completar mercado y costos.
