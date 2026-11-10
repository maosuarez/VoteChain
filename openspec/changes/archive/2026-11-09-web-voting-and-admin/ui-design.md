# UI Design: web-voting-and-admin

## Alcance y principios
- Usuarios: votante (estudiante, uso ocasional, móvil, no técnico) y master (admin, escritorio, uso frecuente).
- Móvil primero (base 360 px); tablet >=768 px; escritorio >=1024 px.
- Densidad: votante baja (una decisión por pantalla); master media (tablas).
- Una acción primaria por pantalla. Tono cálido, preciso, sin jerga cripto ("papeleta", "comprobante"; nunca "transacción", "firma ciega").
- Estilo: fondo `#FFFFFF`/`#F5F6F8`, texto `#14181F`, primario `#1F4FD8` (blanco sobre él 7.5:1), éxito `#0F7B3F`, error `#B3261E`, aviso `#8A5A00`. Tipografía sistema sans, 16 px base/1.5; títulos 24/20 px. Espaciado base 8 px. Radio 8 px.

## Rutas
- Votante: `/votar` (código) -> `/votar/papeleta` -> `/votar/revisar` -> `/votar/comprobante`.
- Master: `/master` (login), `/master/elecciones`, `/master/elecciones/[id]` con pestañas Categorías, Candidatos, Censo, Estado.

## Flujo del votante

### V1 Código
```
┌──────────────────────┐
│ Elecciones 2026-1    │
│ Ingresa tu código    │
│ [ ______ ]           │
│ [   Continuar   ]    │
│ ¿No llegó? Pedir otro│
└──────────────────────┘
```
- Input único, `autocomplete="one-time-code"`, `inputmode` según formato, pegado permitido, mayúsculas normalizadas, espacios ignorados.
- Estados: vacío (botón deshabilitado con `aria-disabled`), validando (spinner + "Verificando..."), error, éxito (paso directo).
- Errores (inline, bajo el campo, `role="alert"`): "Este código no es válido. Revisa que lo copiaste completo." / "Este código ya fue usado." / "Este código venció. Pide uno nuevo." / "La votación no está abierta." (con fechas si existen).
- Mensaje de privacidad fijo bajo el botón: "Tu voto no queda ligado a tu nombre."
- Riesgo: el votante cree que "ya fue usado" es fallo. Copy debe indicar que solo hay un voto por persona y dónde pedir ayuda.

### V2 Papeleta (una categoría por paso)
```
┌──────────────────────────┐
│ Categoría 1 de 2         │
│ Profesor                 │
│ Elige 3, en orden        │
│ ┌ 1.º lugar · 3 pts ───┐ │
│ │ [Elegir candidato ▾] │ │
│ └──────────────────────┘ │
│ ┌ 2.º lugar · 2 pts ───┐ │
│ ┌ 3.º lugar · 1 pt  ───┐ │
│ [Atrás]      [Siguiente] │
└──────────────────────────┘
```
- Encabezado fijo con progreso textual ("Categoría 1 de 2"), no solo barra.
- 3 ranuras ordenadas, cada una con posición y puntos visibles (texto, no solo color/medalla).
- Selección por ranura: pulsar abre selector (hoja inferior en móvil, popover en escritorio) con lista de candidatos (nombre, dependencia/foto opcional con alt vacío), buscador si >8 candidatos.
- Sin repetir: un candidato ya elegido aparece en el selector deshabilitado con etiqueta "Ya es tu 2.º lugar" (visible, no oculto, para que se entienda por qué). Opción "Cambiar" en la ranura; elegir en otra ranura un candidato ya usado NO lo mueve en silencio.
- Siguiente habilitado solo con 3 ranuras llenas; si se pulsa incompleto: foco a la primera ranura vacía y mensaje "Falta elegir tu 2.º lugar."
- Estados ranura: vacía, llena, error. Estados lista: cargando (skeleton), vacía ("No hay candidatos en esta categoría. Avisa al administrador."), error de red con "Reintentar".
- Borrador en `sessionStorage` (sin identidad); se pierde al cerrar.
- Decisión abierta (context.md): voto en blanco / menos de 3. v1 asumido: obligatorio completar 3. Si se aprueba blanco, añadir botón secundario "Dejar esta categoría en blanco" con confirmación.

### V3 Revisar
- Resumen por categoría: lista ordenada "1.º Nombre · 3 pts", "2.º ... · 2 pts", "3.º ... · 1 pt"; enlace "Editar" por categoría (vuelve a V2 conservando datos).
- Aviso: "Al confirmar, tu papeleta no se puede cambiar."
- Botón primario "Confirmar mi voto" (ancho completo móvil, sticky abajo); secundario "Volver".
- Estados: enviando (botón deshabilitado, "Enviando tu voto...", no cerrar), error recuperable ("No pudimos enviar tu voto. Tu selección sigue guardada. Reintentar"), error terminal (código ya usado, elección cerrada) con salida clara. Reintento idempotente: evitar doble envío.

### V4 Comprobante
- Título "Tu voto quedó registrado" (foco al `h1`, `aria-live` polite).
- Muestra: identificador de comprobante (`tx_id`, fuente mono, partido en bloques de 4), fecha/hora UTC con zona local, botones "Copiar" (feedback "Copiado") y "Descargar .txt", enlace "Verificar en el explorador público" (`/explorer`).
- Texto: "Guarda este número. Sirve para comprobar que tu voto está en la cadena. No revela por quién votaste."
- No muestra picks (evita compra/coerción de votos; coherente con no prometer resistencia a coerción). No hay "volver a votar".
- Si el envío se confirma pero el comprobante tarda: estado "Confirmando en la red..." con polling y tiempo máximo, luego mensaje con instrucción para reintentar la consulta sin reenviar.

## Panel master

### Layout
```
Móvil: barra superior + menú hamburguesa     Escritorio: ┌Nav ┬ contenido ─┐
┌─────────────────┐                          │Elecc.│ Título + acción  │
│ ☰ VoteChain  ⎋ │                          │Salir │ Pestañas + tabla │
│ Elección ▾      │                          └──────┴──────────────────┘
└─────────────────┘
```
- Login master (usuario/clave o token de `master-admin-api`); sesión con cierre por inactividad y aviso previo.
- Tablas en escritorio; en <768 px cada fila pasa a tarjeta apilada. Acciones por fila en menú "Acciones" (botón >=44 px).

### Elecciones (lista)
- Columnas: nombre, estado (insignia con texto + icono: Borrador, Abierta, Cerrada), fechas, votos emitidos/censo. Acción primaria "Nueva elección". Vacío: "Aún no hay elecciones. Crea la primera."

### Detalle (pestañas)
- Categorías: lista editable (nombre, orden); añadir/renombrar/eliminar solo en Borrador. Defaults `administrativo`, `profesor`. Vacío con CTA.
- Candidatos: por categoría, alta manual y carga CSV (vista previa con errores por fila antes de aplicar). Un candidato no puede estar duplicado en una categoría. Editar/eliminar solo en Borrador.
- Censo: carga CSV de correos institucionales (vista previa: válidos, duplicados, dominio no aceptado); contadores habilitados/código enviado/votó (sí/no, nunca por quién). Acciones por fila: reenviar código (confirmación), deshabilitar. Búsqueda por correo. Datos personales solo aquí, nunca en la cadena.
- Estado: tarjetas Censo, Códigos enviados, Votos emitidos, Participación %; sin ranking hasta el cierre (decisión vigente). Línea de tiempo: Borrador -> Abierta -> Cerrada. Refresco cada 15 s con "Actualizado hace Xs".
- Abrir votación: botón primario habilitado solo con prerrequisitos listos (>=1 categoría, >=3 candidatos por categoría, censo cargado); lista de prerrequisitos con check/pendiente. Modal: "Al abrir, categorías y candidatos quedan bloqueados. ¿Abrir ahora?".
- Cerrar votación: acción destructiva, modal con resumen (votos/censo) y confirmación escrita (teclear nombre de la elección). Tras cerrar: enlace a resultados/auditoría y aviso "Resultado definitivo; no se puede reabrir".
- Errores de API: banner `role="alert"` con causa y "Reintentar"; formularios con error por campo.

## Componentes
- Button (primario/secundario/peligro; estados hover, focus, disabled, loading).
- TextField con etiqueta visible, ayuda, error. Select/Combobox (patrón ARIA combobox) y BottomSheet.
- RankSlot (posición, puntos, candidato, acciones), CandidateOption (normal, seleccionado, deshabilitado con motivo).
- Stepper textual, Modal confirmación (con foco atrapado), Toast/Banner, StatusBadge, DataTable/CardList, CSVUploader con preview, CopyField.

## Accesibilidad (WCAG 2.2 AA)
- Contraste texto >=4.5:1, texto grande/UI >=3:1; estado nunca solo por color (texto + icono).
- Todo operable con teclado; orden de foco lógico; foco visible 2 px `#1F4FD8` con offset; sin trampas salvo modales (Esc cierra, foco vuelve al disparador).
- Etiquetas `<label>` reales; errores enlazados con `aria-describedby`, resumen de errores al enviar con foco; `role="alert"` para fallos, `aria-live="polite"` para progreso/éxito.
- Cada pantalla: un `h1`, landmarks (`header`, `main`, `nav`), `title` único por ruta, foco al `h1` al cambiar de paso.
- Objetivos táctiles >=44x44 px, separación >=8 px; `viewport` sin bloqueo de zoom; reflow a 320 px sin scroll horizontal; texto escalable al 200%.
- Selector de candidatos: patrón combobox/listbox con flechas, Enter, Esc; opciones deshabilitadas con `aria-disabled` y motivo leído.
- `prefers-reduced-motion`: sin animaciones no esenciales; transiciones <=200 ms. Soporte `prefers-color-scheme` con contrastes verificados.
- Sin temporizadores que expulsen al votante sin aviso; expiración de sesión avisa 60 s antes con opción de extender.
- Idioma `lang="es"`; copy en lenguaje llano (nivel lectura bajo-medio).
- Verificación: axe en CI, prueba manual con teclado y lector (NVDA/VoiceOver) en V1-V4, prueba en móvil real de 360 px.

## Riesgos de usabilidad
- Votante confunde orden/puntos: mostrar siempre posición + puntos junto a cada nombre.
- Doble envío en red lenta: botón bloqueado + idempotencia en servidor.
- Copiar código del correo con espacios: normalizar.
- Master abre/cierra por error: prerrequisitos visibles y confirmación escrita al cerrar.

## Evolución
- v1: lo anterior. v2: voto en blanco (si se decide), CSV de resultados, plantillas de correo editables, modo oscuro manual, idiomas.
