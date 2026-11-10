# Guía del master: despliegue y operación del piloto

## Despliegue
1. `uv run votechain init --validators 3` (3 a 5): genera `.env` (permisos 600) con token, clave del master y claves de validador. No se versiona.
2. Edita en `.env` las variables `VOTECHAIN_SMTP_*`. **Sin `VOTECHAIN_SMTP_HOST` se usa un buzón de desarrollo que guarda los códigos en claro: no usar en el piloto real.**
3. `docker compose up --build -d`. API en `127.0.0.1:8000`, frontend en `127.0.0.1:3000`, explorador en `/explorer/`. Los validadores no se publican. Para exponerlo, usa un proxy TLS y `VOTECHAIN_BIND`.
4. Diagnóstico: `docker compose exec api votechain status` y `... votechain check` (código de salida 0 solo si todos los nodos tienen la misma cadena válida).

## Ciclo de una elección (CLI; dentro del contenedor `api` o con `--env .env --api http://127.0.0.1:8000`)
`votechain election create ID` -> `category ID NOMBRE` -> `candidate ID CATEGORIA CAND_ID NOMBRE` -> `voters ID censo.csv` (una columna de correos; se rechaza completo si hay una fila inválida) -> `code ID correo` (envío/reenvío) -> `open ID` -> (votación) -> `close ID` -> `tally ID`.
El conteo solo se publica al cierre.

## Recuperación
- Reinicio de cualquier servicio: el estado está en volúmenes (`/data`: cadena, censo, hashes de códigos, claves de emisión). Cadena persistida inválida = el proceso no arranca (no se borra nada automáticamente; investigar).
- Un validador caído detiene la cadena cuando le toca el turno; la API responde 503 y la acción **no** se aplicó. Levanta el validador: se sincroniza y las transacciones pendientes se reenvían solas.
- Las claves de emisión viven en `api-data`. Respáldalas junto con `auth.db`; si se pierden, los votantes que no canjearon no podrán hacerlo.

## Límites conocidos
Correlación por tiempo/IP entre canje y voto (recomienda votar con retraso y desde otra red); parada con validador en turno caído (sin view-change); token de master estático; todas las claves de validador en un `.env` de un host; claves de emisión sin cifrar en disco; no resiste coerción ni compra de votos.
