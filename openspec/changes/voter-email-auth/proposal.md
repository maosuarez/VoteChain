## Why

Hay que comprobar que quien vota es una persona habilitada sin exponer su identidad en la cadena. La universidad ya usa códigos por correo; se mantiene esa experiencia con mejores garantías.

## What Changes

- Censo de votantes (fuera de la cadena) cargado por el master.
- Generación y envío por SMTP de un código de un solo uso, con expiración, guardado solo como hash.
- Endpoint para canjear el código y marcar al votante como "ya recibió credencial" (límite de reenvíos y de intentos).
- Registro de auditoría de emisiones sin vincular a votos.

## Capabilities

### New Capabilities
- `voter-roll`: censo de votantes habilitados por elección.
- `email-code-auth`: emisión, expiración, un solo uso y límite de intentos de códigos.

### Modified Capabilities
<!-- Ninguna -->

## Impact

- Código: `auth/`, cliente SMTP, almacenamiento (SQLite) de censo y códigos.
- Depende de: `voting-domain-borda`. Habilita: `anonymous-credentials`.
- Decisión abierta: proveedor SMTP y fuente del censo.
