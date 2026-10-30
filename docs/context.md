# votechain

## Descripción
Proyecto de aprendizaje: construir una blockchain desde cero y evolucionarla hasta un sistema de votación para elecciones de un capítulo estudiantil. El objetivo principal es entender cómo funciona una cadena por dentro; el producto final debe ser utilizable en un piloto real. Todo debe ser gratis y sin dependencias de redes externas.

## Stack
- Python (lenguaje principal), `cryptography` (SHA-256, Ed25519), `pytest`
- API: FastAPI
- CLI: Rich
- Explorador web: Next.js
- Despliegue local: Docker / docker compose (3-5 nodos)

## Arquitectura
- Cadena permisionada propia, sin Ethereum ni testnets.
- Consenso: PoW simple primero (didáctico), luego reemplazado por Proof of Authority (validadores conocidos, rotación round-robin).
- Capas: `block` → `blockchain` → `transactions` → `network (P2P)` → `consensus` → `voting (dominio)` → `api / cli / web`.
- La cadena es un log inmutable; las reglas de votación son validación determinista sobre ese log (máquina de estados).
- Estructura inicial:
  - `votechain/block.py`, `votechain/blockchain.py`
  - `tests/test_blockchain.py`
  - `demo_tamper.py`

## Convenciones
- Serialización canónica para hashear: JSON con claves ordenadas, sin espacios, UTF-8.
- El campo `hash` nunca se incluye en su propio cálculo.
- Timestamps: UTC, entero en segundos.
- Bloque génesis fijo y determinista (`prev_hash` de ceros).
- Type hints en todo el código; tests con `pytest` para cada regla de validación.
- Nombres técnicos en inglés (clases, funciones, archivos); explicaciones en español.

## Restricciones técnicas
- No usar PoW ni consenso público: la red es permisionada.
- Sin servicios de pago ni redes externas.
- Sin ZK-proofs en el alcance (solo como extensión futura).
- Privacidad: nivel A (voto pseudónimo) en el MVP; nivel B (firmas ciegas) como objetivo.
- No prometer que el sistema sustituye elecciones vinculantes a gran escala (coerción, compra de votos y auditabilidad ciudadana no se resuelven con blockchain).

## Decisiones ya tomadas
- Lista de votantes habilitados firmada por un administrador de elección.
- Transacciones del dominio: `CREATE_ELECTION`, `REGISTER_VOTER`, `CAST_VOTE`, `CLOSE_ELECTION`.
- Reglas: un voto por votante, solo dentro de la ventana de tiempo de la elección.
- Se construye por fases (ver `ROADMAP.md`), entendiendo cada concepto antes de pasar a la siguiente.

## Contexto de negocio
- Usuario final: miembros de un capítulo estudiantil que votan en su elección interna.
- Perfil del desarrollador: estudiante de ingeniería con nivel técnico avanzado; prioriza entender sobre copiar.
- Caso de uso objetivo: elecciones de organizaciones pequeñas y medianas (capítulos, semilleros, asociaciones, juntas) donde importan la transparencia y la auditoría.
