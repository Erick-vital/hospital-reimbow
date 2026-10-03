# Validación V1 — entrega local

Fecha: 2026-10-02. V1-01–07 completadas, con los límites documentados abajo.
No implica uso clínico, autenticación real, firma válida ni preparación productiva.

## V1-02 — Arranque y persistencia

Implementación: [API](../backend/src/hospital/main.py),
[configuración](../backend/src/hospital/core/config.py),
[sesiones](../backend/src/hospital/core/database.py),
[Compose](../compose.yaml) y
[migración inicial](../backend/migrations/versions/0001_initial_institutional_identity_and_.py).
Comandos reproducibles: [guía de desarrollo](desarrollo-v1.md).

Entorno: CPython 3.12.3/Linux x86_64; paquetes instalados desde el lock con SHA256.
`pip check`: **No broken requirements found**. Docker 29.8.0/Compose 5.5.1.
PostgreSQL medido: **18.6 (Debian 18.6-1.pgdg12+2)**. Imagen oficial
`postgres:18.6-bookworm@sha256:3725f4e2499eef5134592b3b4ab79a543ed7f8e533b05b5b637af926630f6650`.

| Criterio | Evidencia observada |
|---|---|
| Base vacía llega al esquema por migraciones | `hospital_test` tenía cero tablas antes de upgrade; después seis, incluida `alembic_version=0001`. Desarrollo también migrado. |
| Migración reproducible y repetible | Upgrade repetido a head y `alembic check` en ambas bases, sin operaciones nuevas. |
| Configuración validada | Rechazo de SQLite/driver incorrecto, host remoto local, URL insegura de pruebas y producción con identidad simulada. Errores de arranque sin valor sensible. |
| Bases separadas | Test conecta a hospital_test; su usuario no puede conectar a hospital_dev. |
| Integridad de persistencia | UUID/fecha con zona, valores por defecto, identidades únicas, CHECK, FK y asignaciones sin duplicados comprobados en PostgreSQL. |
| Sesión y rollback | Escritura no confirmada desaparece al cerrar sesión; filas de pruebas se revierten. |
| Arranque HTTP real | Uvicorn temporal arranca y devuelve live 200/ready 200. |
| Caída y recuperación | Mismo proceso API: base detenida → live 200/ready 503; reinicio → ambos 200. |
| Credenciales/correlación | Respuesta 503 y logs API sin contraseñas ni trazas; UUID y X-Request-ID coinciden. |
| Volumen persistente | Rol ficticio conserva el mismo UUID tras detener/reiniciar PostgreSQL. |
| Preparación conserva configuración | Segunda ejecución del generador conserva `.env`, permisos 600; Compose conserva el volumen. |

Suite ejecutada: **26 passed, 1 warning in 0.68s**, código 0.
Diez casos de integración usan PostgreSQL; dieciséis casos de configuración/salud.
Warning: Starlette anuncia deprecación futura del uso de HTTPX en TestClient y propone
HTTPX2. No hubo fallo; no se silenció ni se cambió el lock en esta fase. Reconsiderar
el cliente de pruebas al actualizar dependencias, con comprobación de compatibilidad.

Comando de aceptación ejecutado:

```sh
backend/.venv/bin/python backend/scripts/verify_phase2.py
```

[Resultado estructurado](evidencia/v1-02-resultados.json) conserva tablas antes/después,
versión, revisión, estados HTTP y persistencia. El verificador conserva una única
probe ficticia en la base de pruebas, sin cambiar datos de desarrollo salvo migraciones.

## Incidentes y límites

- La instalación pip encontró DNS denegado en sandbox; se repitió con permiso efectivo
  y terminó correctamente. Sin instalación de paquetes del sistema.
- TestClient se detuvo en sandbox después de los casos de configuración; se interrumpió
  ese proceso y se repitió fuera del sandbox: 16/16 pasaron. Verificador y suite completa
  funcionaron fuera del sandbox. No se atribuye el bloqueo a FastAPI.
- Al cerrar V1-02: migración inicial limitada a identidad/permisos; semilla y
  protección se implementaron después en V1-03. Auditoría/pacientes/episodios pendientes.
- T05 del contrato se comprueba en su parte V1-02 (base vacía, salud, persistencia);
  preparación completa de datos y recorrido siguen en V1-07.
- No se ejecutó downgrade destructivo. No hay ensayo de restauración de backups,
  rendimiento productivo ni pruebas de concurrencia clínica en esta etapa.
- API temporal detenida; PostgreSQL queda activo. El directorio sigue sin Git operativo.


## V1-03 — Identidad local y autorización

Implementación: [resolución del actor](../backend/src/hospital/identity/dependencies.py),
[semilla](../backend/src/hospital/identity/seed.py),
[permisos](../backend/src/hospital/authorization/service.py),
[proyecciones](../backend/src/hospital/authorization/projections.py) y
[ruta protegida](../backend/src/hospital/identity/routes.py).
Se reutilizan esquema 0001, PostgreSQL 18.6 y lock de V1-02; sin nuevas dependencias.

| Criterio | Evidencia observada |
|---|---|
| Semilla explícita/idempotente | Cuatro actores, tres roles y ocho permisos en hospital_dev/hospital_test. Dos ejecuciones conservan UUID. Pruebas conservan suspensiones y filas ajenas. |
| Integridad de semilla | Discrepancia de proveedor, permisos/roles adicionales o inactivo reactivado rechaza y revierte toda la preparación. |
| Identidad ausente/inactiva/desconocida | 401 con mismo código/mensaje, incluso cabecera vacía, demasiado larga o repetida; correlación sin datos del actor. |
| Matriz de permisos | Tres actores activos × ocho operaciones compuestas; permisos suficientes → 200, insuficientes → 403 mediante rutas exclusivas del test. |
| Cabeceras sin autoridad | X-Role/X-Permissions no elevan permisos; usuario de otro proveedor no se selecciona por X-Dev-Actor. |
| Cambios vigentes | Revocar audit.read → siguiente solicitud 403; suspender usuario → siguiente solicitud 401. |
| Consulta limitada | Ruta de test devuelve sólo seis campos para consulta-demo; admisión/supervisor añaden cuatro demográficos. Campos extra nunca se serializan. Permiso demográfico aislado no concede lectura. |
| Episodios | Proyección de siete campos sin demografía; listar exige admissions.read y patients.read; crear identidad verificada exige permiso adicional. |
| Aislamiento | Modo apagado rechaza actor conocido sin consultar base; producción con bandera activa falla en la fábrica real. |
| HTTP real | Uvicorn temporal: actores activos 200 en desarrollo habilitado, resto 401; desarrollo apagado y producción apagado dan 401. Salud pública 200. |

Suite final: **58 passed, 1 warning in 1.55s**, sin fallos ni omisiones.
Incluye 32 casos nuevos y 26 de regresión. Integración utiliza hospital_test;
filas y cambios de cada caso se revierten mediante transacción externa/savepoints.
El verificador deja los actores ficticios en ambas bases, sin borrar datos.

```sh
backend/.venv/bin/python backend/scripts/verify_phase3.py
```

[Resultado estructurado](evidencia/v1-03-resultados.json) registra suite, semilla,
versión, estados HTTP y rechazo productivo. Ejecutado con permisos efectivos para
TCP/TestClient. No detiene PostgreSQL ni cambia la configuración privada.
APIs temporales finalizadas; DEV_IDENTITY_ENABLED sigue false.

Límites: `/identity/me` sólo permite revisar la identidad ficticia resuelta y sus
permisos; no autentica personas. Las rutas clínicas reales llegarán en V1-05/06 y
usarán estos controles/proyecciones; las rutas de prueba no se publican en la API.
S01/S05 se comprueban en su parte de autorización/proyección; quedan pendientes
las comprobaciones con pacientes/episodios persistidos. T03 completo para el
proveedor local. Al cerrar V1-03 la auditoría estaba pendiente; se implementó después en V1-04.
No se declara aptitud productiva ni se integra un proveedor real. Permanece el
warning de deprecación de TestClient documentado en V1-02.

## V1-04 — Auditoría

Implementación: [modelo](../backend/src/hospital/audit/models.py),
[migración 0002](../backend/migrations/versions/0002_audit_events.py),
[servicios](../backend/src/hospital/audit/service.py),
[ruta restringida](../backend/src/hospital/audit/routes.py) y
[pruebas PostgreSQL](../backend/tests/test_audit_postgresql.py).
Mismo entorno/lock de V1-02/03, sin nuevas dependencias.

| Criterio | Evidencia observada |
|---|---|
| Migración | 0002 aplicada en hospital_dev/hospital_test, upgrade repetido y alembic check sin diferencias; siete tablas, sin borrar datos. |
| Éxito transaccional | Registrador exige transacción del servicio, inserta/flush y no hace commit. Acciones patients.create/admissions.create: fallo real de INSERT del evento y fallo posterior a su inserción revierten tanto recurso ficticio como evento. Observación desde nueva sesión. |
| Datos de creación | Evento conserva UUID, actor, fecha del servidor, correlación y snapshot con campos explícitos; excluye claves extra, incluso dentro de identificadores. |
| Lecturas/búsquedas | Metadatos vacíos; se rechaza intentar guardar datos personales como new_values. Si falla la auditoría de consulta, HTTP 503 sin página ni evento de éxito. |
| Denegación independiente | Transacción de recurso abierta mientras el evento se confirma en otra conexión; PID PostgreSQL distinto comprobado. Tras rollback del recurso, evento denied persiste. |
| HTTP real | Sin actor/inactivo → 401; consulta/admision → 403; supervisor → 200. Cada correlación identifica un evento persistido en hospital_test, sin filtro ni datos del recurso denegado. |
| Permisos y paginación | audit.read obligatorio antes de consulta; filtros de acción/UUID, límites, offset, página vacía con total correcto y orden creado/id. Página y total comparten una sentencia; no devuelven evento del propio acceso. |
| Integridad en base | CHECK de acción/resultado/tipo, actor requerido para éxito, JSON objeto y denegación mínima; FK restrictiva del actor. |
| Superficie API | Sólo GET /audit; POST/PUT/PATCH/DELETE dan 405. Sin endpoint para insertar eventos. /identity/me también audita su acceso. |
| Error inesperado del servidor | API Uvicorn exclusiva de test provoca excepción con marcadores personales/token/SQL: 500 genérico, log sólo código/correlación; sin marcadores ni traceback. Salud sigue 200. |
| Canal caído y logs | PostgreSQL inaccesible al guardar denegación conserva 401 y deja AUDIT_DENIAL_UNAVAILABLE con código/correlación; pruebas excluyen URL, contraseña ficticia, token, cabecera de actor y parámetro personal. |

Suite final: **85 passed, 1 warning in 3.22s**, cero fallos/omisiones.
27 casos nuevos más los 58 de regresión. PostgreSQL medido 18.6; mismas dependencias.
Permanece el warning de deprecación de TestClient documentado en V1-02.

```sh
backend/.venv/bin/python backend/scripts/verify_phase4.py
```

[Resultado estructurado](evidencia/v1-04-resultados.json): revisiones/tablas de ambas
bases, suite y matriz HTTP con persistencia. Ejecutado con permisos efectivos para
TCP/TestClient; no reinicia PostgreSQL. APIs temporales cerradas; bandera local
false al cierre. No se imprimen credenciales ni se conserva salida con secretos.

Límites: pacientes/episodios aún no existen; rollback se prueba con una fila ficticia
de Role como recurso de la unidad de trabajo, usando las acciones/snapshots clínicos
del contrato. T01 sobre pacientes/episodios reales queda para V1-05/06/07; no se
anticipa esa aceptación. La infraestructura V1-04 y las rutas ya disponibles están
comprobadas. Pruebas ordinarias revierten filas mediante savepoints; los eventos de
denegación del canal independiente y de la verificación HTTP quedan como evidencia
ficticia en hospital_test y no se borran. Repetir la suite añade eventos de prueba.
V1 no protege frente a un administrador PostgreSQL con permisos de escritura ni
acredita cumplimiento normativo, autenticación real o preparación productiva.

Incidente corregido: en la versión instalada de Starlette, ServerErrorMiddleware
vuelve a lanzar errores inesperados después del handler 500; Uvicorn podría imprimir
el contenido de la excepción. Se comprobó en su código local y se contuvo el fallo
en el middleware de petición de la API. La prueba HTTP real
[test_error_logs_http.py](../backend/tests/test_error_logs_http.py) confirma respuesta
y logs saneados. Límite: respuestas JSON de V1; no se implementan streams ni tareas
externas cuya política de errores habría que comprobar por separado.
## V1-05 — Pacientes mínimos

Implementada por solicitud de continuar la siguiente fase el 2026-10-02 (hora local).
Ejecución registrada en UTC en [informe](evidencia/v1-05-resultados.json).
PostgreSQL estaba detenido tras reinicio: se inició el contenedor existente con
`docker compose --env-file backend/.env start`, conservando su volumen y semilla.
No se instalaron dependencias, modificó el sistema ni desplegó fuera del equipo.

Comando comprobado desde la raíz:

```sh
backend/.venv/bin/python backend/scripts/verify_phase5.py
```

- **147 pruebas pasan**, cero fallos/errores/omisiones, sobre el lock vigente.
- Migración 0003 aplicada y repetida en hospital_dev/hospital_test; Alembic check
  sin diferencias. Secuencia, función de folio, pacientes, identificadores y referencias.
- P01/P04/P05/A01: altas independientes con UUID/folio únicos, lectura y Location;
  desconocidos conservan null/[] sin CURP/nacimiento inventados.
- P02/A02/S01: folio, nombre y TEST/CURP estructural; filtros AND, literales %/_,
  acentos, paginación y candidatos homónimos sin fusión. Consulta omite demografía.
- P03: rechazos por búsqueda ausente, ajena, aleatoria, expirada o incompatible;
  exactos repetidos entre todos los identificadores dan 409 sin revelar el existente.
- S02/T01: fallo al insertar auditoría y después de insertarla revierte paciente/evento;
  próximo folio mayor sin reutilización. Función conserva 13 dígitos mediante secuencia
  temporal de prueba, sin reiniciar la real. Búsqueda revierte referencia/evento juntos.
  Lecturas no entregan datos si falla el registro de auditoría.
- S05/T04: 401/403, identidad verificada sólo con permiso, campos extra/futuros/vacíos,
  límites y enum inválidos; CHECK/FK/UNIQUE en PostgreSQL. API sin edición/borrado.
- **T02 concurrente real**, provisional y verified: dos APIs/conexiones con barrera
  antes del INSERT y después de la comprobación exacta. PIDs PostgreSQL distintos,
  exactamente 201/409; un paciente, un identificador y un evento de creación.
  El perdedor no deja evento de éxito ni recurso parcial.
- HTTP real: paciente verified 201, lectura 200, consulta limitada 200,
  creación sin permiso 403, repetido 409, búsquedas exactas y dos desconocidos.
  Eventos comprobados desde otra sesión; API temporal finalizada en finally.
- Logs del servidor temporal sin credenciales, token sintético ni traceback.
  API permanece deshabilitada por defecto; PostgreSQL activo y bases en 0003.

Fallos resueltos durante la implementación: Alembic comparaba el DEFAULT volátil de
expiración contra su representación normalizada y detectaba una diferencia falsa;
se usa la expresión canónica PostgreSQL y check pasa en ambas bases. Pruebas previas
esperaban rutas/tablas/revisión 0002 y pacientes 404; se actualizaron al alcance real
0003/401. La comparación de timestamps de auditoría/JSON usa el instante, porque
+00:00 y Z representan UTC. No fueron fallos de las reglas transaccionales.

Contrato revisión 3 corrige rango de búsqueda por nombre a 1–302: el anterior 2–300
impedía alta con nombre válido de un carácter o tres componentes de 100.
Alternativa descartada: restringir nombres del alta. Pruebas verifican ambos extremos.
Referencia por folio sirve para seleccionar existentes, no para alta de folio nuevo.

Límites: sin idempotencia de altas sin identificadores, edición, fusión ni transiciones
de verificación. La reserva global también se aplica a provisionales; conflicto no
confirma identidad. CURP sólo valida estructura. A04/S03/S04/S06 de relación con
urgencias/episodios siguen pendientes de V1-06/07. T01 de episodio aún pendiente.
Datos persistidos son exclusivamente ficticios; pruebas con savepoints revierten
sus filas, mientras concurrencia, rollback e HTTP conservan pacientes/acuse/auditoría
en hospital_test como evidencia. El verificador no crea pacientes en hospital_dev.
Warning Starlette/TestClient ya documentado; suite vigente funciona.

## V1-06 — Episodios mínimos

Implementada por solicitud explícita de fase 6 el 2026-10-02 (hora local).
PostgreSQL ya activo y saludable; volumen y datos conservados. Sin instalaciones,
modificaciones del sistema ni despliegue. [Resultado estructurado](evidencia/v1-06-resultados.json).

Comando reproducible desde la raíz:

```sh
backend/.venv/bin/python backend/scripts/verify_phase6.py
```

**199 pruebas pasan**, cero fallos/errores/omisiones; 52 casos nuevos respecto a
V1-05. Warning Starlette/TestClient ya documentado, sin cambio de dependencias.
Migración 0004 aplicada/repetida a ambas bases; Alembic check sin diferencias.

| Criterio | Evidencia observada |
|---|---|
| A03/A04/A05/S04 | Paciente provisional totalmente desconocido abre emergency sin CURP/nacimiento/nombre ni datos administrativos. Paciente admite emergency repetido, outpatient e inpatient; UUID/folios independientes. |
| Relación y lectura | Location y GET conservan campos del episodio, paciente, autor/fecha; sólo los siete campos del contrato. Consulta-demo lee/lista sin recibir demografía del paciente. |
| Paginación | Paciente existente sin episodios devuelve página vacía; paciente inexistente 404. Limit/offset validados, total correcto incluso fuera de página, aislamiento entre pacientes y desempate de fechas por UUID probado. Total/página en una sentencia. |
| S05 | Actor ausente/inactivo/desconocido 401; consulta-demo 403 al crear aun con paciente inexistente. Servicios autorizan antes de consultar; listado requiere ambos permisos de lectura. admissions.create no concede ni exige lectura de paciente. |
| T01 real | Fallo al insertar auditoría y después de insertarla revierte episodio/evento, observado desde otra sesión; el siguiente folio no reutiliza el fallido. Lectura/listado responden 503 sin datos cuando falla auditoría. Denegaciones persisten independientemente. |
| S03/T04 | UNIQUE folio, CHECK type/status/folio, NOT NULL y FK paciente/autor probados directamente en PostgreSQL. Borrar paciente con episodio viola FK; paciente/episodio permanecen. Cuerpo rechaza campos del servidor y fuera de alcance. |
| Carrera de referencia | Recurso ficticio sin actividad eliminado desde otra conexión después del SELECT y antes del INSERT: FK falla, servicio revierte y traduce a 404 sin episodio/evento parcial. No existe borrado por API. |
| Concurrencia permitida | Dos conexiones PostgreSQL/PIDs distintos y barrera antes de INSERT crean dos episodios emergency para el mismo paciente: dos UUID/folios distintos y exactamente un evento de creación para cada uno. |
| Folio | Secuencia bigint NO CYCLE independiente de pacientes; función mantiene ancho mínimo doce y conserva 13 dígitos mediante secuencia temporal de prueba sin reiniciar la persistente. |
| HTTP real | Búsqueda → paciente conocido/desconocido → cuatro episodios cada uno → lectura/listado; 201/200, 401/403/404. Recursos/eventos visibles desde conexión independiente. GET/POST únicos previstos en OpenAPI. |
| Auditoría y logs | Crear guarda snapshot restringido; leer sólo metadatos vacíos y UUID de episodio. Listar guarda acción/actor/correlación con resource_id null; sin copiar filtro ni usar UUID de paciente como episodio. Logs sin credenciales, identificador sintético ni traceback. |

Contrato revisión 4 precisa lo implementado; campos, tipos y permisos no cambian.
Pruebas y verificadores anteriores se actualizaron para esquema/rutas/head 0004;
JSON históricos conservados. Primera suite de 197 pruebas pasó; dos casos añadidos
(carrera de FK y permiso de creación sin lectura) elevan la verificación final a 199.
No se encontró bloqueo ni fue necesario instalar o corregir dependencias.

API temporal cerrada, PostgreSQL sigue activo, identidad local apagada por defecto.
Sólo hospital_test conserva pacientes/episodios ficticios de las verificaciones de
rollback/concurrencia/HTTP; resto de filas de test revierte por savepoints.
Sin idempotencia de POST episodios: repetir abre otro. No hay edición, cierre,
conversión, camas, cargos ni eliminación ordinaria. La protección FK no afirma
inmutabilidad ante administradores de base ni cumplimiento clínico/productivo.
S06 de conservación de estas entidades tras reinicio, migración nueva y medición
local de rendimiento quedan para V1-07. V1 no está declarada entregada todavía.

## V1-07 — Validación y entrega

Aceptación ejecutada el 2026-10-02, hora local de Monterrey (2026-10-03 UTC):

```sh
backend/.venv/bin/python backend/scripts/verify_phase7.py
```

[Script de aceptación](../backend/scripts/verify_phase7.py),
[preparación idempotente](../backend/scripts/prepare_local.py),
[resultados y muestras](evidencia/v1-07-resultados.json) y
[guía de reproducción](desarrollo-v1.md#preparación-y-entrega-v1-07).

| Criterio | Resultado comprobado |
|---|---|
| Suite final sobre PostgreSQL | 199 passed, cero fallos/errores/omisiones, 9,59 s. Incluye servicios, restricciones, rollback real de paciente/episodio/auditoría y dos conexiones con barrera; no se sustituyó concurrencia por operaciones secuenciales. |
| T05: preparación idempotente | Dos ejecuciones de prepare_local.py conservan exactamente todas las filas y valores de secuencias de desarrollo/test (hashes registrados); conserva contenido y permisos 600 de .env. pip check pasa, migraciones/semilla repetidas. |
| T05: base nueva | Base aislada sin tablas migra 0001→0004; once tablas finales, segundo upgrade sin cambios y Alembic check sin diferencias con modelos. No se borró ni reemplazó una base existente. |
| S06: persistencia | Comparación de todas las filas/secuencias de ambas bases antes/después de stop/start idéntica. Relectura HTTP de paciente/episodio idéntica, listado conserva relación y auditoría persiste. |
| Salud y recuperación | Mismo proceso Uvicorn y pool: caída live 200/ready 503 DATABASE_UNAVAILABLE; recuperación ready 200. APIs temporales cerradas y PostgreSQL restaurado. |
| Recorrido entregable | Búsqueda → alta provisional → emergency → lectura/listado → supervisor consulta auditoría. Consulta-demo no crea (403). API con identidad apagada rechaza incluso cabecera supervisor-demo (401). |
| T03 y configuración final | Suite verifica rechazo production con identidad simulada; prepare_local.py también rechaza APP_ENV=production antes de modificar configuración o iniciar servicios. .env mantiene DEV_IDENTITY_ENABLED=false. |
| Datos y logs del recorrido final | Sólo ficticios; logs técnicos de APIs temporales sin contraseñas, identificador TEST del recorrido ni Traceback. |

El diagnóstico añadió **1.000 pacientes ficticios** mediante búsqueda/alta HTTP;
hospital_test tenía **1.042 pacientes** durante la medición, incluidos resultados
conservados de pruebas anteriores y de la suite final. Creación del lote: 14,54 s.
HTTP loopback, un worker Uvicorn, SQLAlchemy/Psycopg síncronos, pool 5+5,
auditoría activa, concurrencia 1. Cada filtro usa diez solicitudes de calentamiento
y cien medidas; percentiles por rango más próximo. Nombre devuelve una página
del conjunto coincidente, mientras folio y TEST buscan el paciente exacto.

| Búsqueda | Medidas | Errores | p50 (ms) | p95 (ms) | Máximo (ms) |
|---|---:|---:|---:|---:|---:|
| Folio | 100 | 0 | 7,622 | 10,347 | 13,859 |
| Nombre | 100 | 0 | 11,657 | 15,185 | 58,940 |
| TEST | 100 | 0 | 7,857 | 10,783 | 16,194 |

Equipo medido: Intel Core i5-12400F, doce procesadores lógicos, MemTotal
32.570.464 kB, Linux 6.14.0-37 x86_64, CPython 3.12.3 y PostgreSQL 18.6.
Se conservan las trescientas muestras en JSON. No hubo umbral de SLA ni prueba
de gran volumen o carga concurrente de búsquedas; PAT-RNF-001/ADM-RNF-002
siguen diferidos como cumplimiento. No extrapolar estos tiempos a producción.

Incidencias y corrección: el sandbox bloqueó Docker/TCP local; la ejecución
autorizada fuera del sandbox permitió comprobarlos. El primer intento de base
nueva utilizó hospital_test como propietario/conexión y chocó con la validación
de usuarios independientes de Settings. Se corrigió a hospital_dev para la base
aislada, manteniendo hospital_test separada, y se repitió la aceptación completa.
La base vacía del intento fallido
`hospital_v1_validation_f3c837a9c4a7477a83dec1b025b02db8` se conserva;
la validada es `hospital_v1_validation_0c47ace2959746c8a5e5720004010434`.
No se relajó Settings ni se eliminó evidencia. El modo production sólo se utiliza
para migrar ese nombre aislado en loopback sin API/semilla/identidad simulada;
no es una prueba de despliegue productivo. Warning TestClient/HTTPX sigue vigente.

V1-01–07 quedan completas dentro del alcance backend local. PostgreSQL permanece
activo, APIs de verificación cerradas e identidad deshabilitada por defecto.
Sin idempotencia de POST, edición/borrado, autenticación real, frontend, firma,
flujos clínicos completos, respaldos/restauración productivos o cumplimiento
normativo validado. La revisión funcional humana y el alcance de la siguiente
versión quedan pendientes de definición; no se declara una aprobación manual.
