## 1. Backend: prueba de Merkle y comprobante

- [x] 1.1 Añadir `merkle_proof` en `merkle.py` y la ruta `GET /chain/receipts/{tx_id}` en `api/app.py`; verificar con `tests/test_merkle.py` (la prueba reconstruye `merkle_root` para 1, 2, 3 y 5 hojas) y `tests/test_api_public.py` (200 con campos exactos sin sender/firma/picks, 404 desconocido).

## 2. Lógica de verificación en JS y paridad

- [x] 2.1 Crear `web/verify.js` (SHA-256 puro, JSON canónico, hash de bloque, Merkle, verificación de cadena, prueba de inclusión, conteo local) y `tests/vectors/audit_vectors.json` generado por el backend; verificar con `tests/js/parity.test.js` (Node) y `tests/test_web_parity.py` (vectores coinciden con el backend; ejecuta el test Node y se omite si no hay `node`).

## 3. Explorador estático

- [x] 3.1 Crear `web/index.html`, `web/app.js`, `web/style.css` (bloques, transacciones, verificación, ranking solo al cierre, comprobante por `tx_id`) y montarlo en `/explorer`; verificar con tests de API (200 sin auth en `/explorer/` y `/explorer/verify.js`; el código estático no contiene `/admin`, correo ni código).

## 4. Cierre

- [x] 4.1 Actualizar `docs/context.md` (explorador, política de ranking), suite completa con pytest, `openspec validate public-audit-explorer --strict` y revisión con code-review-graph.
