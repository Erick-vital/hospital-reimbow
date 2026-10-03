# Contrato V2 — revisión 2, ampliación administrativa

Fecha: 2026-10-03. Lecturas y servicios administrativos comprobados en V2-02A;
POST V2 e idempotencia pendientes de V2-02B. Frontend pendiente.
Ampliación aprobada por el usuario con «ok hazlo entonces»; revisión visual no realizada.
Base: [contrato V1, revisión 4](contrato-v1.md).
Alcance y exclusiones: [plan V2](../plans/v2-interfaz-admision.md).

## Recorrido, campos y permisos

Se conservan `/api/v1` y sus esquemas para clientes existentes. Las rutas ampliadas
usan `/api/v2`; comparten identificadores, secuencias, filtros, errores y servicios.
Paciente, ficha administrativa y episodio siguen siendo conceptos distintos;
el expediente clínico no está implementado. No hay edición ni eliminación.

Campos, ausencias, verificación, permisos y compatibilidad se precisan en
[campos V2](campos-v2.md), parte normativa de este contrato local.
Se añaden identificación administrativa, contactos/domicilios múltiples, descripción
del desconocido y datos del ingreso. verified V2 requiere dos identificadores
contrastados y evidencia de fuente/actor/fecha; V1 sin evidencia se distingue como
declaración anterior. admitted_at es fecha clínica, distinta de created_at.
La cobertura sigue siendo parcial: prioridad/triage, camas y flujos completos diferidos.

| Vista | Datos y recorrido |
|---|---|
| `/patients` | Elegir folio exacto, nombre o identificador CURP/TEST; filtros combinados con AND. Página de 20, anterior/siguiente según total. Selección explícita de coincidencia. Sin consulta global al entrar. |
| `/patients/new` | Provisional por defecto; identidad y perfil administrativo, listas de teléfonos/domicilios/contactos y razones de ausencia. Verificado requiere permiso y evidencia sobre nombre más nacimiento/CURP. Capturar → buscar → revisar → confirmar. |
| Alta desconocida | Búsqueda unidentified=true; alta is_unidentified=true, provisional, nombres/nacimiento null, identificadores []; descriptores opcionales separados. La etiqueta nunca se envía como nombre. |
| `/patients/:id` | Nombre disponible, folio PAC y estado siempre visibles; sólo campos presentes en la proyección autorizada. Episodios paginados con folio EPI, tipo, estado y fecha. |
| `/patients/:id/admissions/new` | Resolver paciente y permiso; tipo emergency/outpatient/inpatient, ingreso, sede/servicio, procedencia y motivo. Confirmar paciente/folio, tipo y campos conocidos/pendientes. Urgencias admite datos pendientes. |
| `/admissions/:id` | Resolver episodio y luego su paciente con permisos independientes; mostrar folio EPI separado de PAC. Si falta permiso de paciente, no mostrar datos del contexto anterior ni permitir abrir otra atención desde esa vista. |
| `/audit` | Sólo `audit.read`; filtros `resource_id`/`action`, página y metadatos de auditoría V1 restringidos al supervisor. |

No se interpreta parecido como identidad confirmada. Una búsqueda por folio selecciona
un existente, pero no respalda un alta nueva. Con identificadores, buscar uno de los
pares del alta; sin ellos, buscar el nombre completo; sin ambos, `unidentified=true`.
El servidor vuelve a comprobar todos los identificadores y la compatibilidad del acuse.
Una coincidencia no impide registrar un homónimo sin identificador ya reservado.

Corrección respecto al texto preliminar del plan: V1 **no consume** `search_id`.
Vence a los 15 minutos; V2 conserva esa regla. El cliente muestra la hora de búsqueda
orientativa; la vigencia la decide PostgreSQL. Cambiar datos invalida el paso de revisión
y obliga a buscar de nuevo antes de confirmar. Una URL directa de alta abre captura
vacía; no reconstruye búsquedas o borradores desde la URL.

El selector de actores sólo existe con modo local explícito (`VITE_DEMO_IDENTITY=true`
y servidor de desarrollo); no se incluye en builds normales. El backend exige además
`APP_ENV=development|test` y `DEV_IDENTITY_ENABLED=true`. Consultar `/identity/me`;
las acciones dependen de los permisos recibidos. Build o cambio de selector no habilitan
el backend. Actores ficticios V1 conservados; nuevo admissions.read_intake para
admision-demo/supervisor-demo, además de admissions.read, protege intake sensible.

## Idempotencia de altas

La cabecera `Idempotency-Key` es opcional en POST V1 para conservar clientes anteriores,
y obligatoria en POST V2 `/patients` y `/admissions`; ausencia en V2 da 422
VALIDATION_ERROR. Sin ella en V1 se mantiene 201 sin garantía de reintento.
El cliente V2 siempre envía UUID v4 aleatorio, generado con
`crypto.randomUUID()`, por intención confirmada. La API acepta UUID v4 en texto
canónico (mayúsculas/minúsculas equivalentes), normaliza a UUID y rechaza cabecera
vacía, repetida, otro formato o versión con 422 `VALIDATION_ERROR`.

Registro en PostgreSQL: actor interno, operación versionada
(`v1.patients.create`, `v2.patients.create`, `v1.admissions.create`, `v2.admissions.create`),
clave, huella SHA-256, UUID del recurso, fecha y vencimiento. UNIQUE sobre
`(actor_id,operation,key)`, FK restrictivas a actor/recurso. Estado interno `pending`
admite temporalmente ambas referencias null; `completed` exige exactamente una
referencia del tipo correcto mediante CHECK. Un constraint trigger diferido al commit
comprueba la fila vigente y rechaza reservas todavía pending: no puede confirmarse
una clave sin recurso. Probar esa restricción también con SQL directo, sin servicio.
No guardar cuerpos ni respuestas en esta tabla.
La huella no anonimiza los datos; el acceso a la tabla sigue restringido.

Huella versión 1: modelo Pydantic validado, valores por defecto y `null` explícitos,
Unicode NFC/espacios e identificadores normalizados como V1; identificadores ordenados
por system/value; fechas ISO y UUID canónicos. JSON UTF-8 con claves ordenadas,
sin espacios y `ensure_ascii=false`, precedido por operación y versión de huella.
En pacientes excluir únicamente `search_id`: es evidencia temporal, no dato de la
intención. Episodio V1 incluye patient_id/type; V2 además todos los campos de intake.
Paciente V2 incluye perfiles/descriptores, razones de ausencia y evidencia declarada.
Reordenar identificadores o renovar acuse compatible no cambia la intención;
cambiar nombre, fecha, estado, datos ampliados, evidencia o tipo sí.

| Caso con clave | Resultado previsto |
|---|---|
| Primer alta válida | 201, recurso, `Location`, `Idempotency-Replayed: false`, `Idempotency-Expires-At` UTC ISO. |
| Misma clave/huella antes de vencer | 200, mismo UUID/folio y Location, `Idempotency-Replayed: true`, mismo vencimiento; proyección con permisos actuales. |
| Misma clave con datos distintos | 409 `IDEMPOTENCY_CONFLICT`; no mostrar huella/cuerpo ni recurso de otro contexto. |
| Competidor espera más de 5 s | 409 `IDEMPOTENCY_IN_PROGRESS`, `Retry-After: 1`; resultado incierto, reintentar misma clave/cuerpo. |
| Clave confirmada ya vencida | 409 `IDEMPOTENCY_EXPIRED`; consultar/reconciliar antes de otra intención. |
| Rollback antes de commit | Sin registro exitoso, recurso ni auditoría de creación; reintento permite volver a validar/crear. Huecos de secuencia son válidos. |
| Otro actor u otra operación | Espacio de claves independiente, con permisos y reglas normales; no reutiliza ni revela resultado ajeno. |

Garantía de replay: 24 horas desde la creación confirmada, reloj PostgreSQL; replay
no renueva el plazo. La clave vencida conserva su registro como reserva indefinida
en V2: no se borra/reutiliza ni permite una segunda alta. No se promete devolver el
resultado por POST después del plazo; las lecturas ordinarias siguen disponibles.
Sin trabajo de limpieza en esta versión. Revisión futura de retención requiere
nuevo contrato y migración, sin borrar pacientes ni auditoría.

Algoritmo previsto: autorizar operación (incluida verificación) antes de consultar
clave; abrir transacción, `SET LOCAL lock_timeout='5s'`, intentar reserva UNIQUE con
`INSERT ... ON CONFLICT DO NOTHING`; si otro commit ganó, comprobar su registro;
si es nueva, validar búsqueda/paciente, crear recurso, enlazar registro, marcar
completed y auditar;
confirmar todo junto. No hay reserva exitosa visible sin recurso. El conflicto de
lock de esa reserva revierte y se traduce a IN_PROGRESS; otros errores conservan
su tratamiento V1. No usar un mutex en memoria ni un SELECT previo como garantía.
`lock_timeout` se limita a la espera por la reserva, restaurando el valor anterior
antes de ejecutar las reglas de negocio. Pruebas deben demostrar ese alcance.

Replay confirmado no exige acuse aún vigente ni repite detección de identificadores;
sí valida estructura de entrada y permisos actuales. No exige permiso de lectura
adicional al de creación: devuelve la proyección de la operación de alta y versión
correspondientes, sin ampliar campos por replay. Revocar
creación/verificación da 403 antes de revelar el registro; revocar demografía omite
esos campos. Actor suspendido/modo apagado da 401. Ninguna respuesta antigua guardada.

La creación registra una sola acción de éxito V1. Cada replay autorizado registra
`patients.replay` o `admissions.replay`, recurso, actor, nueva correlación y metadatos
vacíos, en la misma transacción que su consulta; si falla auditoría no hay respuesta
de éxito. Ampliar CHECK de acciones en migración. Denegaciones conservan canal V1;
claves/cuerpos/huellas no aparecen en logs ni metadatos del replay. Cada solicitud
recibe un `X-Request-ID` nuevo y formato de error V1. Location no cambia.

## Contexto, incertidumbre y caché

Sólo memoria para actor, permisos, borradores, clave y cuerpo congelado. Sin datos
personales en URL, localStorage, sessionStorage, IndexedDB, Cache API ni service worker.
El historial contiene únicamente rutas con UUID; filtros de búsqueda viven en memoria.
Cliente `fetch` con `cache: 'no-store'`; API sensible `Cache-Control: no-store`.
No volcar requests/respuestas a consola ni traces/HAR persistentes de pruebas.

AbortController y número de generación por actor/paciente/consulta: cancelar y
descartar respuestas de generaciones anteriores, incluyendo errores tardíos. Cambio
de actor limpia vista y memoria antes de consultar permisos; cambio de paciente limpia
formulario/listas. Navegación atrás o retorno desde bfcache vuelve a validar identidad
y contexto. Cancelar una petición no revierte un commit en el servidor.

Confirmar congela cuerpo/clave y bloquea doble envío. Timeout, corte de red, 500/503
o IN_PROGRESS dejan intención incierta: conservar memoria y ofrecer «Reintentar el
mismo registro», sin edición ni nueva clave. Una respuesta 201/200 muestra folio y
enlace; «Abrir otra atención» crea una intención explícita distinta.

422/409 IDENTIFIER_CONFLICT son rechazos confirmados de esa solicitud: permiten
corregir/buscar; si cambian datos de negocio, crear nueva intención al confirmar.
SEARCH_REQUIRED permite renovar acuse compatible, conservando clave y datos de
negocio. IDEMPOTENCY_CONFLICT no se resuelve inventando otra clave automáticamente:
reconciliar la intención. IDEMPOTENCY_EXPIRED exige consulta antes de volver a crear.

Recarga/pestaña cerrada, cambio de actor o paciente pierden intención en memoria;
mostrar aviso de reconciliación al entrar a cualquier alta, sin reintento automático.
Buscar al paciente o consultar sus episodios; en desconocidos sin folio conocido la
API V1 no permite recuperar un listado global. Pedir revisión del supervisor en
auditoría y advertir que otra alta podría duplicar. No inventar recuperación por
nombre ni un endpoint de recuperación no autorizado. La reconciliación manual no
garantiza identificar por sí sola un desconocido entre varias altas.

401/403 limpian datos del contexto afectado, revalidan identidad y explican acceso
no disponible. 404 muestra recurso no encontrado sin arrastrar ficha anterior.
422 etiqueta campos sin valores del error; 409 explica conflicto; fallos de red/base
permiten recuperar consultas o reintentar intención congelada. Mostrar correlación
cuando existe, sin inventarla si no hubo respuesta. Accesibilidad: etiquetas, foco
en encabezado al cambiar ruta, resumen de errores, estados anunciados y botones
alcanzables por teclado. Medir tiempos locales, sin afirmar SLA.

## Fuentes y comprobación

Decisiones propias de V2: UUID v4, compatibilidad opcional, 24 h, reserva indefinida,
200 replay y espera de 5 s; no son una exigencia normativa. Casos y pruebas en
[validación V2](validacion-v2.md); entorno/fuentes en [evidencia V2-01](evidencia-v2-01.md).
Bloqueos PostgreSQL: [lock_timeout](https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-LOCK-TIMEOUT).
Caché del cliente: [Request.cache](https://developer.mozilla.org/en-US/docs/Web/API/Request/cache).
Los bocetos no demuestran autorización, idempotencia ni integración implementadas.
Backend ampliado/lecturas acreditados en [evidencia V2-02A](evidencia-v2-02a.md).
Idempotencia, POST V2 y recorrido de navegador aún no se acreditan.
