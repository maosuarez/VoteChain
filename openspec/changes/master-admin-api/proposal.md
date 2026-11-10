## Why

El perfil master debe administrar todo el proceso (elecciones, categorías, candidatos, votantes) de forma segura y auditable, expuesto vía API para que lo consuma la interfaz web.

## What Changes

- API FastAPI con autenticación y autorización del rol master.
- CRUD de elecciones, categorías y candidatos; carga de censo; abrir/cerrar elección; reenvío de códigos.
- Cada acción administrativa relevante se registra como transacción firmada en la cadena.
- API pública de solo lectura (cadena, bloques, conteo) y API del votante (canjear código, emitir papeleta).

## Capabilities

### New Capabilities
- `master-admin`: administración de elecciones, candidatos y votantes con autorización.
- `voter-api`: canje de código y envío de papeleta.
- `public-read-api`: lectura pública de cadena y resultados.

### Modified Capabilities
<!-- Ninguna -->

## Impact

- Código: `api/`. Depende de: `voting-domain-borda`, `voter-email-auth`, `anonymous-credentials`.
- Habilita: `web-voting-and-admin`, `public-audit-explorer`.
