# Motor de negocio v0.4

## Principio
No buscamos el vehículo "más barato". Buscamos la combinación:

**descuento + liquidez + evidencia + margen neto + riesgo controlable.**

## Reventa conservadora

1. Comparables activos.
2. Percentil 25 de precios publicados.
3. Descuento por venta rápida.
4. Tope opcional por Fasecolda.
5. Si solo existe Fasecolda, sirve como referencia pero baja la confianza.

Fasecolda no se trata como precio obligatorio ni como transacción efectiva.

## Puja máxima

`REVENTA_CONSERVADORA - COSTOS - UTILIDAD_OBJETIVO`

Cuando la comisión es porcentual sobre la puja:

`PUJA_MAX = (REVENTA - COSTOS_FIJOS - UTILIDAD_OBJETIVO) / (1 + comisión + comisión*IVA_comisión)`

## Score inicial /100

- rentabilidad esperada: 40
- holgura frente a puja máxima: 25
- confianza de valoración: 25
- cantidad de comparables: 10

Posteriormente agregaremos:
- riesgo mecánico;
- historial de siniestros;
- impuestos/prendas;
- liquidez histórica real;
- días promedio hasta reventa;
- costo financiero por días de inventario.

## Decisiones
- COMPRAR
- VIGILAR
- RIESGO
- NO_PUJAR
- SIN_DATOS

Una decisión COMPRAR es una señal cuantitativa, no reemplaza inspección mecánica/documental.
