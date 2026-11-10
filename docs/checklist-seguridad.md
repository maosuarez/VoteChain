# Checklist de seguridad previo al piloto

- [ ] `.env` con permisos 600, fuera de git y de respaldos compartidos; token y claves generados por `votechain init` (no reutilizados).
- [ ] SMTP real configurado (`VOTECHAIN_SMTP_HOST`); no existe `outbox.jsonl` en el volumen de la API.
- [ ] TLS terminado en un proxy inverso delante de API y frontend; `VOTECHAIN_BIND` solo si hay proxy. Añadir CSP y rate limiting en el proxy (no están en el código).
- [ ] Validadores sin puertos publicados (`docker compose ps`); red interna aislada.
- [ ] Cada operador de validador recibe solo su `VOTECHAIN_NODE_KEY_Vn`; borrar las demás del host de cada operador.
- [ ] Disco cifrado en el host de la API (claves de emisión y `auth.db` sin cifrar en reposo); respaldos cifrados.
- [ ] Rotación del token de master antes y después del piloto (cambiar `.env` y reiniciar la API).
- [ ] `votechain check` en 0 antes de abrir y después de cerrar.
- [ ] Lista de validadores de confianza entregada al auditor por un canal distinto de la red.
- [ ] Censo: la fuente y su limpieza están definidas (decisión abierta del proyecto).
- [ ] Se comunicó a los votantes el límite de correlación tiempo/IP y que no hay protección contra coerción.
