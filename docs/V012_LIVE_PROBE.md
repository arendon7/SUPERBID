# v0.12 — Sonda pública real

La v0.12 añade una sonda ejecutable desde GitHub Actions para observar el contrato real que usa el frontend público de Superbid sin almacenar respuestas crudas.

## Artefacto sanitizado
El reporte contiene únicamente:
- host/path y nombres de parámetros de endpoints, nunca valores de query;
- estructura/tipos del JSON, sin valores escalares de origen;
- observaciones normalizadas y explícitamente permitidas: lote, título, ubicación, vendedor, oferta inicial, precio observado, conteo de pujas, estado y cierre;
- anexos clasificados con endpoint sanitizado.

Se eliminan por diseño claves relacionadas con:
- reserva/precio reservado;
- identidad de pujadores/compradores;
- tokens, firmas, sesiones, cookies y credenciales;
- email/teléfono/documentos de identidad.

## Workflow
`.github/workflows/live-probe.yml` se ejecuta al modificar la sonda o manualmente con `workflow_dispatch`.
El resultado se publica durante 7 días como artifact `superbid-public-probe`.

El workflow no requiere secretos ni intenta autenticarse o eludir controles de acceso.
