## Why

La transparencia solo existe si un tercero puede verificar el resultado sin confiar en el administrador.

## What Changes

- Explorador público de bloques y transacciones; ranking con puntos por candidato.
- Verificación en el navegador: recalcular hashes de la cadena y el conteo.
- Comprobante de voto: el votante comprueba que su papeleta está incluida sin revelar su identidad.
- Publicación del ranking según la política decidida (en vivo o al cierre).

## Capabilities

### New Capabilities
- `audit-explorer`: navegación y verificación pública de cadena y resultados.
- `vote-receipt`: verificación de inclusión de una papeleta.

### Modified Capabilities
<!-- Ninguna -->

## Impact

- Código: `web/` (rutas públicas). Depende de: `master-admin-api`.
