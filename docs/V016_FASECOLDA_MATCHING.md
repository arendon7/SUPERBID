# v0.16 — Fasecolda matching e histórico

## Objetivo

Enriquecer cada lote Superbid con una referencia Fasecolda defendible, sin confundir:

- valor guía Fasecolda;
- precio de mercado;
- última puja observada;
- precio de adjudicación confirmado.

## Fuente pública

La Guía de Valores de Fasecolda usa actualmente el backend público:

`https://fasecoldaback.quantil.co/api/`

Flujo usado por el sistema:

1. `busqueda/{texto}` → códigos candidatos.
2. `listacodigosid/consultabycodigo/{codigos}` → ficha, versión y `valorModelo`.
3. `historic/{codigo_homologado_o_actual}/{modelo}` → serie histórica mensual.

Los valores devueltos por Fasecolda se multiplican por 1.000 para expresarlos en COP.

## Matching

El algoritmo trabaja en dos capas.

### 1. Identidad obligatoria

Antes del fuzzy matching, el candidato debe compartir:

- marca real;
- token principal de línea/modelo;
- para modelos de una sola letra (`X TRAIL`, `F 150`), también el token siguiente.

Esto evita falsos positivos como:

- Chevrolet Traverse → Chevrolet Tracker;
- Citroën C4 → Citroën C3;
- Chevrolet NHR → Chevrolet NQR.

### 2. Similaridad de versión

Solo después de superar la compuerta de identidad se calcula similitud entre el título Superbid y la descripción Fasecolda.

Estados:

- `HIGH`: referencia suficientemente clara para utilizar su valor e histórico como referencia principal.
- `MEDIUM`: probable, pero requiere revisión si se quiere usar como versión exacta.
- `AMBIGUOUS`: varias versiones plausibles; usar rango min/mediana/max.
- `UNMATCHED`: no existe referencia compatible suficientemente defendible.

## Histórico

Para matches `HIGH`, se descarga la serie histórica y se conserva en `fasecolda_value_history`.

Ejemplo validado:

- Renault Logan [2] Expression / Life+ MT 1600, modelo 2020.
- código actual: `08033093`.
- código homologado histórico: `08001189`.
- 62 observaciones entre agosto de 2022 y agosto de 2026.
- última observación validada: 18-08-2026, COP 44.700.000.

## Automatización

- cada lote nuevo o cuyo título/año cambie entra en `fasecolda_match_queue`;
- cron: cada 5 minutos;
- máximo: 6 lotes por ciclo;
- errores: backoff exponencial;
- ambiguos van a `REVIEW`;
- no encontrados van a `UNMATCHED`.

## Seguridad y calidad

- no se toca `sale_price_confirmed_cop`;
- no se persiste `reservedPrice`;
- no se usa `winnerBid` para identificar comprador ni adjudicación;
- funciones operativas no son RPC públicas para `anon/authenticated`;
- Fasecolda se trata como referencia comercial, no como precio de transacción.

## Uso en puja máxima

Regla actual:

- `HIGH`: puede alimentar una referencia de valoración, siempre con haircut conservador antes de calcular puja máxima;
- `MEDIUM`: visible para análisis, pero no debe convertirse automáticamente en valor exacto;
- `AMBIGUOUS`: usar rango y, para automatización, preferir el extremo conservador;
- `UNMATCHED`: no usar Fasecolda en la decisión automática.
