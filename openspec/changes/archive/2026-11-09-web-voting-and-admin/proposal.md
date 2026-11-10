## Why

La interfaz de votación debe ser clara y la administración desde el master debe ser cómoda; sin UI el sistema no es utilizable por la comunidad.

## What Changes

- Next.js: flujo del votante (ingresar código → elegir 1.º/2.º/3.º por categoría → revisar → confirmar → comprobante).
- Panel master: elecciones, categorías, candidatos, censo, estado de la votación, apertura/cierre.
- Papeleta que impide repetir candidato y muestra los puntos 3/2/1 de cada posición.
- Accesibilidad y uso en móvil.

## Capabilities

### New Capabilities
- `voter-ui`: papeleta ordenada con validación y comprobante verificable.
- `master-ui`: panel de administración.

### Modified Capabilities
<!-- Ninguna -->

## Impact

- Código: `web/`. Depende de: `master-admin-api`. Diseño con `ui-ux-designer` antes de implementar.
