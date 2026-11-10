## Context

Ver proposal.md. `voting-domain-borda` dejó la credencial como clave del emisor (sin censo). Este change agrega el censo y los códigos por correo como capa `auth` fuera de la cadena; la emisión de credenciales anónimas es el change siguiente (`anonymous-credentials`).

## Goals / Non-Goals

**Goals:**
- Censo por elección, códigos de un solo uso con expiración, solo hash, límites de intentos y reenvíos, auditoría sin vínculo con votos.
- Envío de correo tras una interfaz inyectable.

**Non-Goals:**
- Endpoint HTTP/FastAPI (change de API): aquí se entrega el servicio de canje que el endpoint invocará.
- Cliente SMTP real y elección de proveedor (decisión abierta): solo interfaz `Mailer` y un fake en memoria.
- Emisión de credencial anónima, autenticación del master, fuente del censo (se recibe una lista).
- Integración con `voting.py`: la elegibilidad se aplicará con las credenciales anónimas.

## Decisions

- **Servicio sobre SQLite (`sqlite3` stdlib)**: tablas `voters`, `codes`, `audit`. Cumple "almacenamiento SQLite" del proposal sin dependencias nuevas. `:memory:` en tests.
- **Reloj inyectable (`now: Callable[[], int]`)**: tests deterministas de expiración; timestamps UTC enteros.
- **Mailer como `Protocol` + `FakeMailer`**: el envío real queda diferido; el servicio no conoce SMTP.
- **Código**: 10 caracteres de un alfabeto base32 sin ambiguos (~50 bits) vía `secrets`. Hash = SHA-256 de `election_id:email:code` (sal implícita por contexto), comparado con `hmac.compare_digest`. Trade-off: SHA-256 simple basta por la entropía y el límite de intentos; un KDF lento no aporta con 50 bits aleatorios y complica sin evidencia.
- **Rechazo como motivo (`str`)**: `redeem` y `issue` devuelven `None` o el motivo, igual que `voting.apply`; sin excepciones de control de flujo.. Los motivos son internos (`not_eligible`, `expired`, ...); la capa API deberá unificar la respuesta pública.
- **Un código vigente por votante**: emitir uno nuevo marca los anteriores como invalidados (cuenta contra el límite de emisiones).
- **Intentos fallidos por código**: al llegar al máximo el código se bloquea; el límite global lo acota la cantidad de emisiones.
- **Auditoría**: tabla `audit(election_id, email, event, ts)` con eventos `issued`, `redeemed`, `rejected:<motivo>`; no hay columnas de voto, papeleta ni clave. Se guarda el correo (dato personal) solo off-chain.
- **Indicador "ya recibió credencial"** en `voters`, monótono; bloquea nuevas emisiones.

## Risks / Trade-offs

- [El servicio sabe qué correo recibió credencial] → inevitable para impedir doble emisión; la anonimidad depende de `anonymous-credentials` (firma ciega) para que la credencial no se vincule al correo.
- [Enumeración de censo por respuestas distintas] → la capa API debe unificar respuestas; el servicio expone el motivo interno.
- [SQLite sin concurrencia fuerte] → suficiente para piloto; transacciones simples.
- [Sin SMTP real] → el piloto requiere implementar `Mailer` SMTP tras decidir proveedor.
