# V2-01 — entorno, decisiones y revisión M2-01

Fecha: 2026-10-03. Trabajo autorizado por «continua con v2».
Resultado: contrato revisión 2, campos ampliados, boceto y matriz preparados.
Ampliación aprobada; revisión visual no realizada, desarrollo autorizado.
Entregables: [contrato V2](contrato-v2.md), [bocetos](bocetos-v2.html),
[campos ampliados](campos-v2.md), [matriz/comandos](validacion-v2.md).
No hay frontend conectado ni migración V2 aún.

## Entorno observado

Desde raíz: `node --version` → v20.19.5; `npm --version` → 10.8.2;
`python3 --version` → 3.12.3. Existe `backend/.venv/bin/python`; no existe `frontend/`.
Disponibles ejecutables `/usr/bin/brave-browser`, `/snap/bin/chromium` y
`/usr/bin/firefox`; su presencia no acredita navegador Playwright instalado.

`docker compose --env-file backend/.env ps -a --format json`, fuera del sandbox:
`reimbow-v1-postgres-1` existe, estado exited, ExitCode 0; volumen conservado.
`ps -eo pid,comm | rg 'uvicorn|postgres|vite|pytest|npm'` no encontró procesos del
servicio/API/pruebas tras cerrar la consulta npm fallida. No se arrancó PostgreSQL
ni API; no se midió salud ni se repitieron las 199 pruebas V1 en esta fase documental.
El texto anterior de ESTADO que afirmaba PostgreSQL activo quedó actualizado.

Revisados contrato V1, servicios/rutas/proyecciones de pacientes y episodios,
configuración, guía y requerimientos PAT-RF-001–005, PAT-RNF-002–005/007/008,
ADM-RF-001–004 y ADM-RNF-001/004/005. Los originales permanecen intactos.
Cambios previos en AGENTS, ESTADO y plan V1 conservados; plan V2 ya existía sin
seguimiento en Git. No se hizo commit ni se mezclaron cambios de otros proyectos.

## Contraste de campos solicitado por el usuario

El 2026-10-03 el usuario indicó: «esta en concordancia con docs/requerimientos ?
si es asi los apruebo». Resultado del contraste: concordancia parcial con el alcance
recortado de V2; no cobertura íntegra de los documentos. No registrar aprobación
incondicional de campos ni de M2-01 ante las diferencias siguientes.

| Tema | Documento de origen | Diferencia o cobertura V2 |
|---|---|---|
| Identificación principal | Pacientes §4–5; Admisión §11 | Nombre, apellidos, nacimiento, CURP e identificador interno están respaldados. Sexo, nacionalidad, nacimiento geográfico y otros documentos quedan fuera. TEST es exclusivamente una decisión de pruebas. |
| Estados y verificación | Pacientes §6–7; Admisión §8 | Provisional/verificada es un catálogo reducido. No implementa verificación por campo, procedencia ni confirmación con dos identificadores fiables. Nombre y permiso no acreditan identificación correcta completa. |
| Desconocido | Pacientes §13; Admisión §9 | Alta provisional sin datos inventados compatible; faltan sexo aparente, edad aproximada, características, procedencia, traslado, pertenencias y enriquecimiento posterior. |
| Episodio | Admisión §4.3 y §10 | Paciente, folio, tipo y estado están respaldados. Faltan datos indicados como mínimos: fecha/hora clínica de ingreso, sede, servicio, procedencia, prioridad y datos clínicos/administrativos asociados. created_at es fecha de registro, no fecha clínica de ingreso. |
| Contactos y domicilio | Pacientes §8–10; Admisión §10–11 | Se difieren, aunque son parte de los requerimientos del sistema completo. |

Referencias: [Pacientes](requerimientos/2.%20PACIENTE.md) y
[Admisión](requerimientos/1.%20ADMISION.md). Los documentos narrativos contienen
obligaciones adicionales a los RF/RNF numerados. El recorte del plan explica estas
omisiones, pero no permite afirmar cumplimiento de los módulos completos.
Este contraste corresponde a revisión 1, sustituida por la ampliación aprobada
y concretada a continuación. Conserva la razón del cambio, no describe alcance vigente.

## Ampliación aceptada y concretada

Tras recomendar ampliar perfil, datos descriptivos del desconocido e ingreso,
definir evidencia de verificación y diferir prioridad/triage, el usuario respondió
«ok hazlo entonces». Se registra aprobación de esa ampliación, sin solicitar
otra autorización para los mismos campos. No se infiere recorrido visual ejecutado
ni aceptación clínica/productiva. El diseño acordado está en [campos V2](campos-v2.md).

- Perfil: sexo registrado/nacionalidad, múltiples teléfonos/domicilios/contactos;
  razones de ausencia, con límites y tipos; representación legal/financiera no implícita.
- Desconocido: sexo aparente, rango estimado, características, procedencia/traslado;
  no bloquean urgencia ni inventan nacimiento.
- Ingreso: admitted_at separado de created_at, sede/servicio coherentes, procedencia
  y motivo; permiso nuevo read_intake. Catálogos ficticios, sin gestión de camas.
- verified: nombre más nacimiento/CURP contrastados, fuente por campo, actor/fecha
  servidor y transacción; las declaraciones V1 sin evidencia se distinguen.
- Rutas ampliadas /api/v2 y esquema V1 conservado; idempotencia versionada,
  cubriendo todos los campos nuevos y claves obligatorias en POST V2.
- Prioridad/triage, aseguradoras, camas, cobros, edición/enriquecimiento posterior,
  adjuntos y clínica completa permanecen diferidos. Cobertura parcial documentada.

Plan reorganizado: V2-02A implementará campos/catálogos/verificación/permisos;
V2-02B incorporará idempotencia antes de formularios. Ninguno está implementado
por esta actualización de diseño. No se modificaron backend ni bases de datos.

## Selección de herramientas

Metadatos oficiales npm consultados sin instalar; versiones estables observadas y
selección inicial para V2-03. Compatibilidad declarada, todavía sin build comprobado.

| Paquete | Versión seleccionada | Requisito comprobado |
|---|---|---|
| react / react-dom | 19.3.0 / 19.3.0 | react-dom exige react ^19.3.0. |
| vite | 8.3.2 | Node ^20.19.0 o >=22.12.0; Node disponible satisface. |
| @vitejs/plugin-react | 6.1.1 | Vite ^8.0.0 y mismo rango Node; pares de compilador adicionales opcionales. |
| typescript | 7.0.2 | Node >=16.20.0. |
| react-router | 7.18.4 | Node >=20 y react/react-dom >=18. |
| @types/react / @types/react-dom | 19.3.0 / 19.3.0 | Tipos alineados con React. |
| @playwright/test | 1.63.0 | Node >=20; navegador administrado pendiente. |

React Router 8.4.0 observado requiere Node >=22.22.0, incompatible con el entorno
actual. Se seleccionó el último 7 disponible para evitar actualizar Node/sistema.
No usar `@latest` en la instalación reproducible. Comprobar de nuevo metadatos si
cambia el entorno; fijar versiones directas y lock en V2-03. Los metadatos no
demuestran ausencia de vulnerabilidades ni compatibilidad en ejecución.

React Router en modo declarativo (BrowserRouter); aplicación local SPA, sin SSR.
Cliente HTTP nativo fetch, AbortController y crypto.randomUUID; sin dependencia de
caché persistente. CSS propio y componentes accesibles, sin kit adicional en V2-01.
TypeScript estricto; pruebas de recorrido Playwright sobre API real, regresión backend
con pytest existente. Añadir pruebas unitarias sólo para lógica que lo justifique.

Consultas reproducibles (sin descargas/instalaciones de paquetes):

```sh
node --version
npm --version
npm view react@19.3.0 version engines --json
npm view react-dom@19.3.0 version peerDependencies --json
npm view vite@8.3.2 version engines --json
npm view @vitejs/plugin-react@6.1.1 version engines peerDependencies peerDependenciesMeta --json
npm view typescript@7.0.2 version engines --json
npm view react-router@7.18.4 version engines peerDependencies --json
npm view @playwright/test@1.63.0 version engines --json
npm view @types/react@19.3.0 version --json
npm view @types/react-dom@19.3.0 version dependencies --json
```

La consulta npm interna falló con EAI_AGAIN; reejecutada con permiso fuera del
sandbox, completó. Docker también requirió acceso fuera del sandbox. No se leyeron
ni copiaron credenciales a documentos. No se instalaron herramientas ni se modificó
el sistema. Consultas iniciales de versiones anteriores sólo sirvieron para explorar;
la tabla registra la selección final.

Fuentes oficiales consultadas el 2026-10-03:

- [React: versiones](https://react.dev/versions).
- [Vite: entorno requerido y plantilla React/TS](https://vite.dev/guide/).
- [Vite: host, puerto y proxy](https://vite.dev/config/server-options.html).
- [TypeScript: instalación por proyecto](https://www.typescriptlang.org/download/).
- [React Router: modo declarativo](https://reactrouter.com/start/declarative/installation); requisitos exactos por versión en npm.
- [Playwright: instalación y pruebas](https://playwright.dev/docs/intro).
- Metadatos del registro oficial: [React](https://registry.npmjs.org/react/19.3.0), [Vite](https://registry.npmjs.org/vite/8.3.2), [plugin React](https://registry.npmjs.org/@vitejs%2fplugin-react/6.1.1), [TypeScript](https://registry.npmjs.org/typescript/7.0.2), [router](https://registry.npmjs.org/react-router/7.18.4), [Playwright](https://registry.npmjs.org/@playwright%2ftest/1.63.0).

## M2-01 preparada

Abrir `docs/bocetos-v2.html` como archivo local en el navegador: no necesita API,
base ni instalación. Alternativa desde la raíz, sólo archivos de docs publicados en
loopback (comando preparado; no dejado ejecutándose):

```sh
python3 -m http.server 5174 --bind 127.0.0.1 --directory docs
```

URL: `http://127.0.0.1:5174/bocetos-v2.html`; terminar servidor con Ctrl+C.
Actores y resultados son simulados; el selector del boceto no acredita permisos de API.
Datos: Persona de Prueba Ficticia, PAC-000000000101/102 y EPI-000000000201.

| Paso | Revisión concreta |
|---|---|
| Existente | Buscar coincidencias → seleccionar → ficha → abrir episodio → confirmar → consulta. Comprobar separación de PAC/EPI y paciente siempre identificado. |
| Nuevo | Alta nueva → capturar perfil/listas/ausencias → buscar/revisar → confirmar → ficha. Supervisor requiere nombre+nacimiento/CURP y referencia de fuente para declarar verificación. |
| Desconocido | Búsqueda → registrar identidad desconocida → revisión → alta → urgencias. Comprobar que no exige CURP/nacimiento/nombre. |
| Errores | En revisión de alta, simular identificador reservado y búsqueda vencida; corregir/repetir revisión. |
| Reintento | Abrir episodio → simular respuesta perdida → reintentar mismo registro. Ver folio igual y mensaje de confirmación por reintento. |
| Permisos/contexto | Cambiar a consulta-demo y luego inactivo-demo; ver restricciones/limpieza. Supervisor muestra auditoría y opción verificada. |
| Ingreso ampliado | Urgencias con pendientes; para consulta/hospitalización indicar fecha, sede y servicio. Fecha de ingreso distinta de registro. Sin prioridad/triage. |
| Contrato | Revisar compatibilidad V1/rutas V2, replay 24 h, reserva permanente y reconciliación tras recarga; en desconocidos sin folio no hay recuperación automática. |

La puerta del plan indica «Usuario confirma flujo y campos o registra correcciones;
no sustituir por aprobación del agente». Se recibió y atendió la corrección con
ampliación aprobada. El desarrollo puede continuar sin pedir confirmación repetida;
el recorrido visual queda preparado para revisión, sin atribuir su ejecución al usuario.

## Comprobaciones de esta fase

- JavaScript extraído del HTML a `/tmp/reimbow-v2-bocetos-check.js` y
  `node --check /tmp/reimbow-v2-bocetos-check.js`: exit 0.
- Sin IDs duplicados ni referencias JavaScript a IDs inexistentes; enlaces locales
  de contrato, validación y evidencia comprobados, ninguno faltante.
- `git diff --check`: exit 0. Cambios anteriores conservados.
- ESTADO: 52 líneas, 370 palabras; cumple ambos límites fijos.
- Captura con Brave headless: sandbox rechazó socket; fuera del sandbox el proceso
  no produjo captura y se cerró. **Presentación visual y recorrido manual pendientes**;
  no se afirma prueba de navegador exitosa. El HTML local queda disponible para M2-01.

La comprobación sintáctica y la simulación no equivalen a pruebas de integración V2.

Comprobaciones tras ampliar revisión 2: `node --check` exit 0; HTML sin IDs
duplicados, referencias JavaScript sin destino ni etiquetas/enlaces rotos; todos
los enlaces locales de documentos resueltos, incluyendo rutas con espacios.
`git diff --check` exit 0. ESTADO actualizado: 55 líneas, 372 palabras.
Se añadieron diez casos A01–A10 para ampliar la aceptación prevista; no ejecutados.
No se repitió el intento de captura ni se instaló/arrancó frontend, API o base.
