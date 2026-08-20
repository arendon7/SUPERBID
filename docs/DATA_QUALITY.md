# v0.10 — Calidad histórica y proveniencia

## Problema
Para este negocio, tres valores parecidos significan cosas diferentes:

1. **Oferta inicial**
2. **Última puja observada**
3. **Precio de adjudicación confirmado**

Nunca deben mezclarse.

## Proveniencia
Cada lote puede tener múltiples evidencias:

- `search_index_bootstrap`
- `superbid_rendered_html`
- `superbid_public_json`
- `closing_snapshot`
- `sold_confirmation`
- futuro: `buyer_record`

Cada evidencia guarda:
- fuente;
- URL;
- fecha;
- campos soportados;
- confianza;
- nota.

## Etiquetas de calidad
- `CONFIRMADO`
- `ALTA`
- `OBSERVADO`
- `HISTORICO_INDEXADO`
- `REFERENCIAL`

## Supabase
El proyecto central ya contiene:
- 10 lotes bootstrap;
- 10 evidencias de proveniencia;
- 7 ofertas iniciales recuperadas.

Ninguno de esos valores bootstrap fue convertido en precio final.

## Excel
La hoja Histórico incorpora:
- data_quality
- data_confidence
- data_source_type

Y existe una hoja nueva:
- Proveniencia
