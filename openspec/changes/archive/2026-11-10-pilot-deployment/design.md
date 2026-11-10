## Context

Ver proposal.md. Existen `Node`/`Transport` con `InMemoryTransport` (`network.py`), PoA (`consensus.py`), la API (`api/app.py`, que mina localmente con PoW dificultad 0 sobre una cadena en memoria), `VoterAuth` (SQLite, claves de emisión solo en memoria) y el frontend/explorador. Los changes archivados `p2p-poa-consensus`, `master-admin-api`, `anonymous-credentials` y `web-voting-and-admin` difirieron a este change: (1) que la API use `Node`/PoA, (2) persistir cadena y claves de emisión, (3) CSP/TLS/rotación de token (esto último solo como checklist, ver Non-Goals).

## Goals / Non-Goals

**Goals:**
- Red PoA real (procesos, HTTP) de 3 a 5 validadores + API + frontend con `docker compose`.
- Persistencia de cadena, censo/códigos y claves de emisión; reinicio sin pérdida.
- CLI de operación y auditoría; prueba e2e automatizada con verificación independiente.

**Non-Goals:**
- Auditoría humana por un tercero (no la puede hacer un agente; queda pendiente y documentada).
- View-change/timeouts de PoA, descubrimiento dinámico de pares, cambio de validadores en caliente, TLS/CSP/rate limiting dentro del código (checklist para el operador: se terminan en un proxy inverso), cifrado de claves en reposo, HSM, rotación del token.
- Cambios en reglas de `voting.py`, `blind.py` o formato de bloque.

## Decisions

- **Ampliaciones respecto del proposal** (necesarias por lo diferido): persistencia de cadena/claves de emisión/censo; API sobre `Node`; `SmtpMailer`/`FileMailer`; capacidad `audit` dentro de `operations-cli`. `httpx` pasa a dependencia de runtime; se añaden `uvicorn` y `rich`. No se crean capacidades fuera de las dos del proposal: persistencia, API sobre PoA, correo y e2e se especifican en `deployment`.
- **Transporte HTTP (`HttpTransport`)** como adaptador del `Protocol` existente, con `httpx` síncrono, timeout corto y errores de red tragados (un par caído no rompe el gossip). Pares estáticos `id=url` por configuración. Mensajes: `POST /p2p/tx`, `POST /p2p/block` (202), `GET /p2p/chain`, `GET /p2p/status`. Alternativa descartada: sockets propios o libp2p (alcance).
- **Cola + un hilo de trabajo por nodo**: `Node` es síncrono y su gossip reenvía por el transporte dentro del mismo llamado; con HTTP síncrono y un candado, A->B->C->A bloquearía el candado de A (interbloqueo distribuido). Los endpoints `/p2p/tx` y `/p2p/block` solo encolan y responden; un hilo único aplica los mensajes al `Node` bajo un candado. `/p2p/chain` y la API leen bajo el mismo candado. Alternativa: `Node` asíncrono (reescribir `network.py`), descartada por alcance.
- **Bucle del nodo**: cada `block_interval` (1 s) produce si es su turno y hay mempool; cada `sync_interval` (5 s) hace `sync()` (recuperación de pares caídos y forks, sin notificación de reconexión). Bloques vacíos no se producen: la cadena no crece sin actividad.
- **API sobre el nodo "api"**: nodo PoA sin clave (observador) que se une a la red; `submit` valida con `build_state`, entrega con `Node.submit_tx` (gossip a los validadores) y espera la inclusión hasta `confirm_timeout` (10 s por defecto, configurable); si vence responde 503. La espera libera el candado compartido (si no, el hilo de trabajo no podría aplicar el bloque). Sin `node` la API conserva su comportamiento actual (modo PoW local; los tests existentes no cambian). En 503 de `create_election` la clave de emisión se guarda igual: la validación previa garantiza que el id es nuevo y, si la transacción se incluye después, el canje funciona.
- **Persistencia**: `ChainStore` guarda la cadena como JSON con escritura atómica (temporal + `os.replace`) tras cada cambio; al arrancar se valida con `replace_chain` (cadena completa, firmas PoA) y, si no es válida, el proceso falla en vez de descartarla (fail-closed: descartar silenciosamente ocultaría manipulación). Reescribir todo es O(n): escala de piloto. Las claves de emisión (`IssuerKeyStore`, JSON con permisos 0600) se cargan en `VoterAuth` al arrancar; `VoterAuth` ya admite archivo SQLite. La clave del master y el token siguen viniendo de variables de entorno: no se escriben en datos. Sin cifrado en reposo (checklist: cifrado de disco). Alternativa: SQLite para la cadena, descartada (otra capa sin necesidad).
- **Correo**: `SmtpMailer` (`smtplib`, STARTTLS opcional, credenciales por entorno) y `FileMailer` (JSONL en datos) solo para desarrollo/e2e, con advertencia. Los errores de SMTP se registran sin código ni credenciales y `send_code` responde `sent: false` (la API ya devuelve solo `sent: bool`); `issue_code` captura la excepción del mailer.
- **Configuración por entorno** (`VOTECHAIN_*`): `VALIDATORS` (claves públicas en orden), `NODE_ID`, `NODE_KEY`, `PEERS`, `DATA_DIR`, `MASTER_TOKEN`, `MASTER_KEY`, `SMTP_*`, `WEB_DIR`. Un solo `.env` generado por `votechain init` alimenta compose. Trade-off: todas las claves de validador quedan en un host; para un piloto con operadores distintos cada operador recibe solo su clave (checklist).
- **CLI**: `argparse` (stdlib) con subcomandos y Rich para tablas; `votechain = "votechain.cli:main"`. Subcomandos: `init`, `status`, `check`, `election {create,category,candidate,voters,code,open,close,tally}`, `audit`, y los de proceso `serve-node`/`serve-api` (entrypoints de los contenedores). Sin dependencia de Typer/Click (alcance).
- **Auditoría (`audit.py`)**: función pura que valida cada cadena descargada con `Blockchain(validators=<confianza>)`, compara puntas y recalcula el conteo con `build_state`. Es lo que usan la CLI y la prueba e2e (una sola implementación). El verificador del explorador se ejecuta con Node mediante `scripts/explorer_tally.js`, que reutiliza `web/verify.js` (implementación independiente en otro lenguaje); se omite explícitamente sin Node.
- **Compose**: validadores `v1..v3` y `v4`,`v5` bajo el perfil `extended`; `init` escribe `COMPOSE_PROFILES=extended` si se piden más de 3 y los pares correspondientes. Validadores sin puertos publicados; API y frontend en `127.0.0.1`. Una imagen de backend (`python:3.12-slim`, `pip install .`) para validadores y API con comando distinto; imagen de frontend con `next build` (la URL del API se fija en build porque los rewrites de Next se evalúan ahí). Healthchecks por `/p2p/status` y `/chain`.
- **E2E**: `tests/test_pilot_e2e.py` levanta 3 validadores y la API como servidores uvicorn reales (hilos, puertos efímeros, datos en `tmp_path`, `FileMailer`), y ejecuta el escenario con un cliente `httpx` que hace de votante (cripto real de `blind`). El escenario vive en `votechain/e2e.py` para poder correrlo también contra compose (`python -m votechain.e2e`); esa ejecución contra contenedores no forma parte de la suite. El test también reinicia un validador y la API para cubrir persistencia y recuperación, y manipula una copia de cadena para verificar la detección.

## Risks / Trade-offs

- [Validador en turno caído detiene la cadena; la API responde 503] -> aceptado (sin view-change); `check` lo diagnostica y la guía del master lo describe.
- [Un reinicio entre `create_election` y la persistencia de la clave pierde la clave] -> la clave se guarda justo después de entregar la transacción; riesgo residual documentado en la guía (recrear la elección si ocurre antes de abrirla).
- [Endpoints P2P sin autenticación] -> los bloques exigen firma de validador y las transacciones firma de emisor; los validadores no se publican en el host; autenticación entre pares queda fuera.
- [Todas las claves en un `.env` de un host y claves de emisión en claro en disco] -> checklist (permisos, cifrado de disco, distribución por operador); fuera de alcance cifrar.
- [Reescritura completa de la cadena y sync completo cada 5 s] -> escala de piloto; sin optimización prematura.
- [`FileMailer` guarda códigos en claro] -> solo desarrollo/e2e, advertido; en producción `SMTP_HOST` es obligatorio (la guía lo exige).
- [Correlación tiempo/IP entre canje y voto] -> heredado; la guía recomienda votar con retraso y desde otra red.
- [La auditoría humana no existe aún] -> el e2e automatizado prueba el mecanismo, no sustituye la independencia de un tercero; la guía de auditoría lo prepara y el estado queda "pendiente".

## Migration Plan

Aditivo: la API sin `node` se comporta igual. Despliegue: `votechain init`, `docker compose up --build`. Rollback: `docker compose down` (los volúmenes conservan estado) y revertir el commit.
