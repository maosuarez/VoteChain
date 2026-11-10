## Context

`master-admin-api`, `anonymous-credentials` y `public-audit-explorer` ya dejan la API lista. Este change solo añade la interfaz; no modifica backend ni cadena. Diseño visual en `ui-design.md` (respetado salvo las desviaciones listadas abajo).

## Goals / Non-Goals

**Goals:**
- Flujo del votante y panel master en Next.js, con la criptografía del votante en el navegador compatible byte a byte con el backend.
- Papeleta con validación (sin repetir, 3/2/1) y comprobante por `tx_id`.

**Non-Goals:**
- Voto en blanco (decisión: no existe), SMTP, nuevos endpoints, persistencia del backend, deshabilitar votantes, contadores de censo/códigos (la API no los expone).
- Sustituir el explorador de `web/`.

## Decisions

- **Directorio `frontend/`** (Next.js App Router, TypeScript). `web/` ya es el explorador estático servido en `/explorer`; separar evita colisión. Alternativa: sustituir el explorador, descartada (rompe el change archivado).
- **Sin cambios en el backend ni CORS**: `next.config` reescribe `/api/*` hacia `VOTECHAIN_API_URL` (por defecto `http://127.0.0.1:8000`). El navegador solo habla con el origen de Next. Trade-off: requiere `next start`/`dev`, no export estático.
- **Cripto con `@noble/curves` y `@noble/hashes`** (Ed25519 y SHA-256 en JS puro, auditadas, sin dependencias) y `BigInt` nativo para RSA ciego. Se descarta `crypto.subtle`: Ed25519 no está en todos los navegadores y exige contexto seguro (piloto por HTTP en LAN; mismo motivo que el explorador). El azar usa `crypto.getRandomValues`, disponible sin contexto seguro.
- **Paridad por vectores**: `tests/vectors/voter_vectors.json` generado por el backend (`python -m tests.make_voter_vectors`) con: par Ed25519 desde semilla, firma de mensaje, mensaje de credencial, FDH, cegado con factor fijo, firma ciega, desbloqueo, verificación, y una transacción `CAST_BALLOT` completa (tx_id y firma). Los tests de `vitest` (Node) reproducen los vectores; `tests/test_voter_vectors.py` comprueba que el backend aún los produce y `tests/test_frontend.py` ejecuta `vitest` (se omite sin `node_modules`). Ed25519 es determinista, por lo que la firma debe coincidir exactamente. Además, un test verifica la credencial desbloqueada en JS con `blind.verify` del backend usando un vector.
- **JSON canónico propio** (claves ordenadas recursivamente, sin espacios, Unicode sin escapar), como `web/verify.js`; vectores de `audit_vectors.json` reutilizados. Solo enteros, cadenas, listas y objetos.
- **Credencial en `sessionStorage`** (clave privada del votante + firma + id de elección) entre canje y envío. Riesgo: perderla tras gastar el código deja al votante sin poder votar (el código es de un solo uso). Mitigación: sessionStorage sobrevive a recargas de la pestaña; se borra al cerrar la pestaña y al mostrar el comprobante. Quien controle el navegador podría votar con ella: mismo modelo de amenaza que el código.
- **Transacciones firmadas antes de enviar y guardadas en el borrador** para reintentos idempotentes (Ed25519 determinista; misma marca de tiempo). Si el reintento recibe 400, se consulta `/chain/receipts/{tx_id}` calculado localmente; 200 = ya registrada. Así una respuesta perdida no obliga a un voto nuevo (la credencial ya votó esa categoría).
- **Desviaciones de `ui-design.md`** (obligadas por la API): V1 pide correo además de código (la API canjea por `email` + `code`) y elección (descubierta desde la cadena: se listan solo las abiertas). El comprobante muestra un `tx_id` por categoría (una papeleta por categoría). Panel master: sin contadores de censo/códigos ni deshabilitar votante; "Estado" muestra votos emitidos contados en la cadena; el prerrequisito de censo no se exige (el backend tampoco). Login master valida el token con `POST /admin/elections/{id}/voters` de una elección inexistente con lista vacía: 401 = inválido, 409 = válido, sin efectos.
- **Elecciones descubiertas desde la cadena** (`/chain`, txs `CREATE_ELECTION`) más `/elections/{id}`, como el explorador; sin endpoint de listado.
- **Lógica pura separada de componentes** (`lib/`): papeleta, CSV, cripto, API; los componentes son finos y se prueban con Testing Library.
- **Identificador de candidato** derivado del nombre (minúsculas, sin acentos, guiones); la duplicación se detecta en el cliente y la API lo rechaza igual (409).

## Risks / Trade-offs

- [Token master en sessionStorage, expuesto a XSS] -> sin HTML dinámico no confiable (React escapa); CSP y TLS quedan para `pilot-deployment`.
- [Correlación tiempo/IP entre canje y voto] -> heredado de `anonymous-credentials`; la UI no añade vínculo (no persiste correo junto a la papeleta; el correo solo se usa en el canje).
- [RSA con BigInt no es de tiempo constante] -> el votante solo opera con su propio factor secreto, no hay oráculo; aceptable.
- [Nombres de candidato y correos con CSV mal formado] -> vista previa con errores por fila antes de aplicar.
- [Dependencias npm nuevas] -> versiones fijadas por `package-lock.json`; `frontend/` es opcional para el backend.

## Migration Plan

Aditivo: nuevo directorio `frontend/` y tests de paridad. Rollback: revertir el commit.
