## 1. Vectores de paridad del backend

- [x] 1.1 Crear `tests/make_voter_vectors.py` y `tests/vectors/voter_vectors.json` (Ed25519, FDH, cegado con factor fijo, desbloqueo, verificación, `CAST_BALLOT` completo) y `tests/test_voter_vectors.py`; verificar con `pytest tests/test_voter_vectors.py` (el backend reproduce los vectores).

## 2. Proyecto y lógica pura

- [x] 2.1 Crear `frontend/` (Next.js + TypeScript + vitest, rewrite `/api/*` a la API) y `lib/crypto` (Ed25519, SHA-256, RSA ciego BigInt, JSON canónico, transacción firmada); verificar con `npm test` (paridad exacta con `voter_vectors.json` y `audit_vectors.json` en Node).
- [x] 2.2 Crear `lib/ballot` (3 picks distintos, puntos 3/2/1, motivo de deshabilitado, primera ranura vacía) y `lib/csv` (candidatos y correos con vista previa); verificar con tests de vitest de cada regla.
- [x] 2.3 Crear `lib/api` (cliente, descubrimiento de elecciones, canje, envío idempotente con consulta de comprobante, sesión/credencial en sessionStorage); verificar con tests con `fetch` simulado (400 con comprobante existente = registrada; 401 master).

## 3. Interfaz del votante

- [x] 3.1 Implementar `/votar`, `/votar/papeleta`, `/votar/revisar`, `/votar/comprobante` con componentes RankSlot/CandidateOption/selector accesible; verificar con tests de componentes (sin repetir, ranura incompleta, rechazo uniforme, comprobante sin picks, limpieza).

## 4. Panel master

- [x] 4.1 Implementar `/master`, `/master/elecciones`, `/master/elecciones/[id]` (categorías, candidatos, censo, estado, abrir/cerrar, inactividad); verificar con tests de componentes (login 401/409, prerrequisitos, cierre con texto, duplicado, banner de error).

## 5. Cierre

- [x] 5.1 Actualizar `docs/context.md` y `.gitignore` (frontend), ejecutar pytest completo, tests y build del frontend, `openspec validate web-voting-and-admin --strict` y revisión con code-review-graph.

## Workflow follow-up

- `openspec archive web-voting-and-admin --yes` solo si todo pasa.
