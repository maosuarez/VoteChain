# Guía de auditoría para un tercero independiente

**Estado: la auditoría humana por un tercero está PENDIENTE.** Lo que existe es una prueba automatizada (`tests/test_pilot_e2e.py`, `python -m votechain.e2e`) que ejecuta una elección completa y verifica el conteo por código; prueba el mecanismo, no sustituye la independencia de un auditor.

## Qué necesita el auditor
- Acceso de lectura a las URLs `/p2p/chain` de los nodos (o a `/chain` de la API) y a `/elections/{id}/tally`.
- La lista de claves públicas de los validadores obtenida **por fuera de la red** (de cada operador). No usar la que informe el sistema.

## Procedimiento
1. `votechain audit ID --nodes v1=URL,v2=URL,... --validators PK1,PK2,... --api URL`.
   Valida hashes, Merkle, firmas y turnos con los validadores de confianza, compara todos los nodos, recalcula el conteo desde la cadena y lo compara con el publicado. Con Node instalado (y ejecutando desde el repositorio) añade el verificador del explorador (`web/verify.js`), otra implementación; si se omite lo indica.
2. Código de salida distinto de 0 = discrepancia; la salida indica nodo y bloque.
3. Abrir `/explorer/` y verificar en el navegador: cadena, conteo y un comprobante (`tx_id`) entregado por un votante.
4. Revisar manualmente: número de credenciales emitidas (`audit` de `auth.db`, solo el master) frente a papeletas en cadena, y que la elección se abrió y cerró en el rango publicado.
5. Probar sospecha de manipulación: alterar una copia local de la cadena y confirmar que `audit` falla.

## Límites que el auditor debe conocer
El sistema no impide que el master emita credenciales a no votantes (se detecta comparando emisiones con papeletas); correlación por tiempo/IP; el servidor firma como master.

## Registro de la auditoría
Auditor: _pendiente_. Fecha: _pendiente_. Resultado: _pendiente_.
