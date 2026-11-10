# votechain

## Descripción
Sistema de votación para la Facultad de Ingeniería: cada semestre se elige a los administrativos y profesores que serán honrados por su labor del semestre anterior. Reemplaza el esquema actual (2 votos por persona: 1 administrativo + 1 profesor, y luego elección) por un sistema estilo Balón de Oro, con control de votos sobre una blockchain propia: sin doble voto, trazable, honesta y transparente. Sigue siendo un proyecto de aprendizaje (entender la cadena por dentro), pero el producto debe ser utilizable en un piloto real. Todo gratis y sin redes externas.

## Sistema de votación (Balón de Oro)
- Cada votante elige **3 personas distintas por categoría**, en orden: 1.º = 3 pts, 2.º = 2 pts, 3.º = 1 pt.
- Categorías iniciales: `administrativo` y `profesor`. Son configurables por el master (cada categoría con su propio listado de candidatos y su propia papeleta de 3).
- Un votante no puede repetir candidato en la misma papeleta; una papeleta por votante por categoría.
- Resultado = suma de puntos por candidato, derivada de la cadena; se puede ver el ranking parcial según la política de la elección (ver decisiones abiertas).
- Desempate: más votos de 1.er lugar, luego de 2.º; si persiste, empate declarado.

## Roles
- **Master**: perfil administrador. Crea elecciones y categorías, gestiona candidatos, carga/habilita votantes, abre y cierra la votación, reenvía códigos, ve auditoría. No puede ver quién votó por quién.
- **Votante**: miembro habilitado de la comunidad (estudiante, etc.). Se autentica con código y emite su papeleta.
- **Auditor público**: sin cuenta; consulta la cadena, el conteo y verifica de forma independiente.

## Autenticación del votante (código por correo)
- Modelo actual de la universidad (representantes escolares): llega un código al correo y se usa al votar. Se mantiene la idea.
- Cada votante habilitado recibe por correo institucional un **código de un solo uso**, con expiración, guardado solo como hash en el servidor.
- El código prueba elegibilidad y se canjea por una **credencial anónima** (firma ciega, ver abajo); el voto se emite con esa credencial, no con la identidad.
- Objetivo de seguridad: el sistema sabe *que* una persona habilitada votó (para impedir doble voto) pero no *por quién* votó, y el master no puede vincular credencial con persona.
- Hasta que exista la capa de firmas ciegas, el MVP usa voto pseudónimo (clave por votante), declarado como limitación.

## Stack
- Python (lenguaje principal), `cryptography` (SHA-256, Ed25519, RSA para firmas ciegas), `pytest`
- API: FastAPI
- CLI: Rich
- Web: Next.js (interfaz de votación, panel master, explorador/auditoría pública)
- Correo: SMTP (gratuito; proveedor por definir)
- Despliegue local: Docker / docker compose (3-5 nodos)
- Especificaciones y cambios: **OpenSpec** (`openspec/`), idioma español

## Arquitectura
- Cadena permisionada propia, sin Ethereum ni testnets.
- Consenso: PoW simple primero (didáctico), luego reemplazado por Proof of Authority (validadores conocidos, round-robin).
- Capas: `block` → `blockchain` → `transactions` → `network (P2P)` → `consensus` → `voting (dominio)` → `auth (códigos + credenciales)` → `api / cli / web`.
- La cadena es un log inmutable; las reglas de votación (límite de 3 picks, puntos 3/2/1, un voto por credencial, ventana de tiempo) son validación determinista sobre ese log.
- Datos mutables y sensibles (lista de votantes, hashes de códigos, correos) viven fuera de la cadena; en la cadena solo compromisos/hashes y votos.

## Convenciones
- Serialización canónica para hashear: JSON con claves ordenadas, sin espacios, UTF-8.
- El campo `hash` nunca se incluye en su propio cálculo.
- Timestamps: UTC, entero en segundos.
- Bloque génesis fijo y determinista (`prev_hash` de ceros).
- Type hints en todo el código; tests con `pytest` para cada regla de validación.
- Nombres técnicos en inglés (clases, funciones, archivos); explicaciones y specs en español (encabezados estructurales de OpenSpec y SHALL/MUST en inglés).

## Restricciones técnicas
- Red permisionada; sin consenso público.
- Sin servicios de pago ni redes externas (el SMTP es la única salida externa aceptada).
- Sin ZK-proofs en el alcance (solo extensión futura).
- No prometer que el sistema resiste coerción o compra de votos.

## Decisiones ya tomadas
- Puntuación 3/2/1 con 3 picks ordenados y distintos por categoría.
- Blockchain propia para impedir doble voto, dar trazabilidad y transparencia.
- Perfil master con administración completa de elecciones, opciones, candidatos y votantes.
- Código de un solo uso por correo como mecanismo de acceso del votante.
- Trabajo por changes de OpenSpec.

## Decisiones abiertas
- Visibilidad del ranking: ¿en vivo, o solo al cierre? (ver en vivo puede sesgar votos; el balón de oro lo publica al final).
- Proveedor SMTP y dominio de correo institucional aceptado.
- Quién forma el censo (fuente de la lista de votantes) y de candidatos.
- Número de validadores PoA y quiénes los operan (facultad, estudiantes, auditor externo).
- ¿Se permite votar en blanco / menos de 3 picks?

## Contexto de negocio
- Usuario final: comunidad de la Facultad de Ingeniería (votantes) y administradores del proceso (master).
- Perfil del desarrollador: estudiante de ingeniería con nivel técnico avanzado; prioriza entender sobre copiar.
- Caso de uso: reconocimiento semestral de administrativos y profesores; importa la transparencia y poder auditar el resultado sin confiar en el administrador.
