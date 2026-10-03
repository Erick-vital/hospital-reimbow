# Desarrollo local V1

Comandos comprobados el 2026-10-02 para V1-02–07 en CPython 3.12.3/Linux x86_64,
Docker 29.8.0 y Compose 5.5.1. Ejecutar desde la raíz del proyecto.
Usar exclusivamente datos ficticios. Estado y resultados: [validación](validacion-v1.md).

## Instalación y configuración

```sh
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip --isolated install --no-cache-dir --require-hashes -r backend/requirements.lock
backend/.venv/bin/python -m pip check
python3 backend/scripts/configure_local.py
```

El generador crea `backend/.env` con permisos 600, contraseñas aleatorias para las
**bases de datos** e identidad simulada deshabilitada. Si existe, conserva el archivo
sin reemplazarlo. No imprime credenciales. [.env.example](../backend/.env.example)
documenta nombres de variables sin secretos. No guardar `.env` en control de versiones.
No es un sistema de contraseñas de usuarios del HIS.

La API lee el archivo desde una ruta absoluta del paquete, independiente del directorio
actual; las variables del proceso tienen prioridad. Se valida el driver
`postgresql+psycopg`, conexión loopback en desarrollo/pruebas y base correspondiente.
Pruebas exigen `TEST_DATABASE_URL` hacia `hospital_test` con usuario distinto al de
desarrollo. Producción con identidad simulada falla antes de iniciar.

Se usa el código fuente con `--app-dir`/pythonpath; no se instaló un paquete editable
ni se preparó distribución productiva. El lock incluye herramientas de pruebas.

## PostgreSQL y migraciones

```sh
docker compose --env-file backend/.env up -d --wait
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
APP_ENV=test backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m alembic -c backend/alembic.ini check
APP_ENV=test backend/.venv/bin/python -m alembic -c backend/alembic.ini check
```

PostgreSQL 18.6, imagen oficial `18.6-bookworm` fijada por digest en
[compose.yaml](../compose.yaml); volumen `reimbow-v1_postgres_data` montado en
`/var/lib/postgresql`, conforme al [formato de la imagen PostgreSQL 18](https://hub.docker.com/_/postgres).
Publicación sólo en `127.0.0.1:5432`. El entrypoint crea `hospital_dev` y
`hospital_test` con propietarios/contraseñas independientes, sin privilegios de
superusuario ni creación de bases/roles, y revoca conexión pública entre ellas.
La cuenta administrativa del contenedor se usa sólo para inicialización.

La inicialización sólo ocurre sobre volumen vacío. Volver a ejecutar Compose o el
generador conserva datos/configuración; cambiar `.env` no rota contraseñas ya guardadas
en PostgreSQL. No usar `down -v` ni reiniciar secuencias para preparar la base.
Las pruebas tampoco borran bases ni tablas. El downgrade inicial existe como reversión
de desarrollo pero elimina esas tablas; no fue necesario ejecutarlo ni es paso de preparación.

Migración `0001`: `institutional_users`, `roles`, `permissions`, `user_roles` y
`role_permissions`, con UUID, unicidad, CHECK y FK restrictivas. La semilla explícita
de V1-03 se describe más adelante. `0002` añade audit_events, `0003` pacientes,
identificadores y búsquedas, y `0004` episodios. La aplicación no crea ni migra
tablas automáticamente.

## Arranque y salud

```sh
backend/.venv/bin/python -m uvicorn hospital.main:create_app --factory --app-dir backend/src --host 127.0.0.1 --port 8000 --no-access-log
```

La aplicación muestra OpenAPI en `http://127.0.0.1:8000/docs`. Operaciones de salud disponibles:

- `GET /api/v1/health/live`: 200, `{"status":"alive"}`; no consulta la base.
- `GET /api/v1/health/ready`: ejecuta `SELECT 1`; 200, `{"status":"ready"}`.
  Si la base está caída, 503 con `DATABASE_UNAVAILABLE` y correlación, sin URL/credenciales.

Ambas son públicas. Ready mide acceso a PostgreSQL, no certifica que todas las
migraciones o los futuros servicios estén disponibles. Configurar una sesión por
solicitud; los servicios futuros delimitarán transacciones. Cerrar la sesión revierte
cualquier escritura sin commit. Pool con pre-ping y tiempos acotados de conexión,
espera de pool y consultas; apagar PostgreSQL no impide iniciar/consultar live.

Las respuestas llevan `X-Request-ID` generado por servidor; errores usan el formato
del [contrato](contrato-v1.md). Los logs de errores excluyen excepciones completas,
SQL y credenciales. El comando desactiva logs HTTP de acceso para no registrar filtros
personales en URL cuando existan esas rutas.

## Pruebas reproducibles

Sólo configuración/salud sin servidor PostgreSQL activo:

```sh
backend/.venv/bin/python -m pytest -q -c backend/pyproject.toml backend/tests -m 'not integration'
```

Todas las pruebas con base `hospital_test` migrada:

```sh
backend/.venv/bin/python -m pytest -q -c backend/pyproject.toml backend/tests
```

Verificación completa de la fase, desde la raíz:

```sh
backend/.venv/bin/python backend/scripts/verify_phase2.py
```

El verificador aplica migraciones a ambas bases y comprueba divergencias, ejecuta
pruebas, levanta API temporal en un puerto libre y **detiene/reinicia sólo PostgreSQL
de este proyecto** para probar caída, recuperación con el mismo proceso/pool y
persistencia. Conviene ejecutarlo sin trabajo local simultáneo sobre estas bases.
Restaura PostgreSQL en `finally` ante fallos normales y termina la API temporal.
Conserva un rol ficticio `phase2-persistence-demo` exclusivamente en `hospital_test`;
el resto de filas de pruebas se revierte. No crea pacientes ni datos reales.

Guarda [resultados estructurados](evidencia/v1-02-resultados.json), sin secretos.
En este entorno las pruebas TestClient quedaron detenidas dentro del sandbox;
funcionaron al ejecutar con permisos efectivos fuera de él. Docker/TCP local también
requieren esos permisos. No se modificó el sistema para solucionar la restricción.

## Identidad local y permisos V1-03

Preparación explícita, sin habilitar el modo HTTP ni borrar datos:

```sh
backend/.venv/bin/python backend/scripts/seed_identity.py
APP_ENV=test backend/.venv/bin/python backend/scripts/seed_identity.py
```

Cuatro actores: admision-demo, supervisor-demo, consulta-demo e inactivo-demo;
tres roles y ocho permisos según [matriz del contrato](contrato-v1.md#identidad-y-permisos).
Se ejecuta en una sola transacción. Repetir conserva UUID, filas ajenas y suspensiones;
restaura asignaciones de la semilla que falten. Si hay proveedor/identidad incompatible,
roles adicionales o permisos ajenos a esos roles, rechaza sin cambios parciales.
No ejecutarla para imponer cambios administrativos: revisar primero discrepancias.
Se rechaza en producción aunque la identidad HTTP esté deshabilitada.

Arranque de demostración con bandera sólo en el proceso, manteniendo `.env`:

```sh
APP_ENV=development DEV_IDENTITY_ENABLED=true backend/.venv/bin/python -m uvicorn hospital.main:create_app --factory --app-dir backend/src --host 127.0.0.1 --port 8000 --no-access-log
```

Desde otra terminal:

```sh
curl -sS -H 'X-Dev-Actor: consulta-demo' http://127.0.0.1:8000/api/v1/identity/me
curl -sS http://127.0.0.1:8000/api/v1/identity/me
curl -sS -H 'X-Dev-Actor: inactivo-demo' http://127.0.0.1:8000/api/v1/identity/me
```

La primera devuelve 200 con UUID, actor_key y tres permisos; las siguientes 401
IDENTITY_REQUIRED. `/identity/me` exige actor activo, sin permiso adicional; sólo
expone la identidad resuelta. No es login. Actor desconocido, cabecera vacía/repetida
o modo deshabilitado también dan 401. Cabeceras X-Role/X-Permissions no conceden acceso.
Cada solicitud consulta estado/permisos actuales en una sesión breve independiente,
que se cierra antes del servicio; así no abre una transacción en la sesión de negocio.
La salud sigue pública. Producción con bandera activa falla antes de arrancar.

Las dependencias `permitted` y la función `authorize` comprueban permisos explícitos.
Los servicios futuros deben llamar a `authorize` antes de consultar recursos y usar
las proyecciones de campos explícitas. `patients.read_demographics` amplía campos,
pero exige además el permiso de la operación. No serializar entidades completas ni
usar un modelo de respuesta que vuelva a incluir campos omitidos con valores null.
Los 403 y proyecciones se verifican mediante rutas de test, sin publicar pacientes o
registros clínicos simulados como endpoints reales.

Verificación comprobada de esta fase:

```sh
backend/.venv/bin/python backend/scripts/verify_phase3.py
```

Siembra dos veces ambas bases, ejecuta la suite sobre hospital_test, levanta tres
APIs temporales en loopback para comprobar modos y verifica fallo productivo en
subproceso. Las termina en finally. No reinicia PostgreSQL. Guarda
[resultados sin secretos](evidencia/v1-03-resultados.json). La semilla permanece;
los cambios de negocio de cada prueba se revierten. Desde V1-04 las denegaciones
usarán el canal independiente y conservarán eventos ficticios.
Requiere permisos efectivos para TCP local.

## Auditoría V1-04

Migrar ambas bases con los comandos de la sección PostgreSQL; head es 0002.
La API no migra al arrancar. Nuevo endpoint `GET /api/v1/audit`, disponible con
`audit.read`, que sólo tiene supervisor-demo en la semilla. Arrancar con la bandera
local explícita como en V1-03 y consultar:

```sh
curl -sS -H 'X-Dev-Actor: supervisor-demo' 'http://127.0.0.1:8000/api/v1/audit?action=audit.read&limit=20&offset=0'
curl -sS -H 'X-Dev-Actor: consulta-demo' http://127.0.0.1:8000/api/v1/audit
```

Primero: 200 con `{items,limit,offset,total}`. Segundo: 403 PERMISSION_DENIED.
También admite `resource_id` UUID; los filtros se combinan con AND. Sin filtros
lista eventos según permiso. Orden ascendente `(created_at,id)`; limit 1–100,
offset no negativo. No promete una instantánea entre páginas.
Registra el acceso antes de responder; su propio evento aparece sólo en consultas
posteriores. No hay endpoints para crear, modificar ni eliminar eventos.
Los snapshots de altas incluyen campos personales del contrato y sólo se entregan
con audit.read; usar exclusivamente datos ficticios.

Para integrar V1-05/06: cada ruta sensible declara `name` con su acción canónica
(patients.search/create/read, admissions.create/read/list). Resolver actor con la
dependencia vigente y autorizar antes de leer recursos. El servicio abre
`with session.begin()` y llama `record_success` en esa misma sesión, después de
preparar recurso/proyección y antes de confirmar; éste añade/flush sin commit.
Una excepción debe salir del bloque para revertir recurso y evento. No capturar el
fallo y confirmar el recurso por separado. Para altas, pasar resource_id y snapshot
con campos del contrato; el registrador descarta campos extra. Consultas/búsquedas
sólo guardan referencias/correlación, sin nombres, filtros ni contenidos.

El manejador registra 401/403 de acciones conocidas con `audit_sessions`, una
factoría de sesiones independientes de la unidad de negocio. Actor interno si fue
resuelto, recurso UUID null y metadata sólo código. Si falla ese canal, mantiene
la respuesta de denegación y loguea código/correlación sin excepción ni parámetros.
Los errores inesperados de las peticiones JSON se contienen antes de llegar
a Uvicorn, con log mínimo INTERNAL_ERROR/correlación y respuesta 500 genérica.
Conservar `--no-access-log` para impedir logs HTTP con filtros personales.
No reemplazar audit_sessions por la sesión transaccional del servicio.

Verificación comprobada:

```sh
backend/.venv/bin/python backend/scripts/verify_phase4.py
```

Aplica/repite migraciones y compara modelos en ambas bases, prepara semilla,
ejecuta 85 pruebas y levanta API temporal en loopback con hospital_test para
comprobar 401/403/200 y eventos persistidos. Termina esa API en finally, sin detener
PostgreSQL ni borrar evidencia. Deja eventos ficticios de denegación/consulta en
hospital_test; el resto de las pruebas usa rollback/savepoints. Guarda
[resultados sin secretos](evidencia/v1-04-resultados.json).
Rollback clínico se prueba en el componente con recurso ficticio; las entidades y
rutas reales siguen en V1-05/06. El verificador V1-03 ahora acepta la revisión vigente;
los JSON históricos se conservan como evidencia de su ejecución original.

## Estado al cerrar V1-04

PostgreSQL activo, ambas bases en 0002 y semilla ficticia conservada.
APIs temporales cerradas; identidad simulada deshabilitada por defecto.
Próxima etapa V1-05: pacientes mínimos. Pacientes/episodios aún no tienen rutas.



## Pacientes mínimos V1-05

Head en V1-05: **0003**; desde V1-06, **0004** en ambas bases. Incluye pacientes, identificadores reservados
UNIQUE global, referencias de búsqueda de 15 minutos y secuencia/función de folio.
No borrar ni reiniciar secuencias al preparar el entorno. Los verificadores V1-04/05 también
comprueban ahora el head vigente; su JSON histórico de 0002 permanece intacto.

Arrancar con la bandera explícita de V1-03 y usar sólo datos ficticios:

```sh
curl -sS -H 'X-Dev-Actor: admision-demo' 'http://127.0.0.1:8000/api/v1/patients?identifier_system=TEST&identifier_value=DEMO-MANUAL-001'
```

Copiar el `search_id` devuelto y enviarlo en el alta (sustituir el marcador):

```sh
curl -i -H 'X-Dev-Actor: admision-demo' -H 'Content-Type: application/json' -d '{"search_id":"UUID_DEVUELTO","identity_status":"provisional","given_names":"Persona ficticia manual","identifiers":[{"system":"TEST","value":"DEMO-MANUAL-001"}]}' http://127.0.0.1:8000/api/v1/patients
```

201 devuelve proyección del paciente y `Location`. Consultar esa ruta con
admision-demo (demografía) o consulta-demo (sólo seis campos básicos).
Repetir el mismo identificador da 409, sin UUID/datos del paciente previo.
Si el TEST ya existe, seleccionar su resultado o elegir otro TEST ficticio.
Para verified usar supervisor-demo y nombre; admision-demo recibe 403.

Nombre: subcadena literal, case insensitive, conserva acentos; `%`/`_` literales.
Folio e identificador exactos; filtros AND; limit 1–100/offset ≥0.
Sin filtros da 422. `unidentified=true` devuelve siempre página vacía y acuse
para crear un desconocido sin nombre ni identificadores, conservando null/[];
no sirve para listar todos los desconocidos. Nombre completo del alta debe haberse
buscado si no hay identificadores; con identificadores buscar uno de sus pares.
La referencia debe pertenecer al mismo actor, ser vigente y no contradecir el alta.
Una búsqueda por folio selecciona existentes y no permite un alta nueva.

No reintentar automáticamente altas sin identificadores: no son idempotentes y
pueden crear otro provisional. No hay edición, fusión ni borrado de pacientes.
Episodios implementados en V1-06 según la sección siguiente.

Verificación reproducible (migra/repite, siembra, compara modelos, ejecuta suite y HTTP):

```sh
backend/.venv/bin/python backend/scripts/verify_phase5.py
```

Requiere acceso efectivo a Docker/TCP local y PostgreSQL iniciado con
`docker compose --env-file backend/.env start`. Conserva datos del volumen.
API temporal de prueba se cierra en finally. Conserva pacientes/identificadores
ficticios de concurrencia, rollback y HTTP en hospital_test, sus referencias y
la auditoría; pruebas restantes revierten por savepoints. Desarrollo no recibe
pacientes de prueba. Evidencia: [V1-05](evidencia/v1-05-resultados.json).

## Episodios mínimos V1-06

Head vigente: **0004** en hospital_dev/hospital_test. Migrar con los comandos
iniciales; la API no migra al arrancar. Preparación conserva pacientes existentes.
Arrancar con la bandera explícita de identidad local y `--no-access-log`.

Tras buscar/seleccionar o crear un paciente ficticio como en V1-05, copiar su `id`:

```sh
curl -i -H 'X-Dev-Actor: admision-demo' -H 'Content-Type: application/json' -d '{"patient_id":"UUID_DEL_PACIENTE","type":"emergency"}' http://127.0.0.1:8000/api/v1/admissions
```

201 devuelve episodio y Location; consultar esa ruta o listar por paciente:

```sh
curl -sS -H 'X-Dev-Actor: consulta-demo' 'http://127.0.0.1:8000/api/v1/admissions/UUID_DEL_EPISODIO'
curl -sS -H 'X-Dev-Actor: consulta-demo' 'http://127.0.0.1:8000/api/v1/patients/UUID_DEL_PACIENTE/admissions?limit=20&offset=0'
```

Sustituir los marcadores por UUID reales del flujo de datos ficticios. Lecturas 200,
listado `{items,limit,offset,total}` con orden `(created_at,id)` ascendente.
No entrega nombres, nacimiento ni identificadores del paciente. Crear requiere
admissions.create; leer admissions.read; listar añade patients.read.
Consulta-demo no crea (403), incluso con paciente inexistente; sin actor/inactivo
401. Actor permitido con paciente inexistente recibe 404 sin evento de éxito.
Supervisor puede consultar auditoría filtrando `resource_id` del episodio.
Listados auditan acción/correlación sin copiar filtro ni demografía.

Tipos permitidos: emergency/outpatient/inpatient. Paciente provisional desconocido
puede abrir urgencias con sólo su UUID y tipo. No se exige nuevo search_id para
abrir episodio. Status open, actor, fecha, UUID y folio se generan en servidor;
enviarlos en el cuerpo da 422. No hay cierre, conversión, camas ni cargos.
Varias altas, aun mismo tipo/paciente, crean episodios distintos. No reintentar
automáticamente POST: no promete idempotencia y puede abrir otra atención.
API sin edición/borrado; PostgreSQL impide borrar paciente con episodios.

Verificación comprobada:

```sh
backend/.venv/bin/python backend/scripts/verify_phase6.py
```

Aplica/repite migraciones a ambas bases, comprueba modelos, siembra identidad,
ejecuta suite PostgreSQL y API temporal en loopback. Recorrido con paciente de
nombre conocido y desconocido, cuatro episodios para cada uno, lectura limitada,
listado paginado, 401/403/404 y auditoría confirmada desde otra sesión.
Finaliza API en finally; no reinicia PostgreSQL ni borra datos.
Conserva pacientes/episodios ficticios de rollback, concurrencia y HTTP en hospital_test;
pruebas ordinarias revierten con savepoints. No crea episodios en hospital_dev.
[Evidencia V1-06](evidencia/v1-06-resultados.json). La entrega final se describe abajo.

## Preparación y entrega V1-07

Después de instalar el venv con el lock, este comando prepara configuración,
PostgreSQL, migraciones y semilla de ambas bases:

```sh
backend/.venv/bin/python backend/scripts/prepare_local.py
```

No instala paquetes. Requiere Docker disponible y APP_ENV development/test con
DEV_IDENTITY_ENABLED=false. Conserva `.env`, filas, secuencias y suspensiones;
no borra ni reinicia bases. Repetido dos veces conserva exactamente las filas y
secuencias de todas las tablas en ambas bases. Se rechaza producción y una
identidad simulada ya habilitada. La habilitación HTTP sigue siendo explícita
por proceso, como muestran los comandos anteriores.

Aceptación completa reproducible:

```sh
backend/.venv/bin/python backend/scripts/verify_phase7.py
```

Requiere acceso TCP a loopback y Docker; no debe ejecutarse mientras otra sesión
use esta base, porque detiene y vuelve a iniciar sólo PostgreSQL del proyecto.
Comprueba preparación dos veces, migración 0001→0004 en una base nueva,
suite completa PostgreSQL, API con identidad apagada (401), flujo HTTP con
identidad habilitada explícitamente en test, 403 y consulta autorizada de auditoría.
Mantiene el mismo proceso API durante caída (live 200/ready 503) y recuperación.
Compara todas las filas/secuencias antes y después del reinicio y relee paciente,
episodio y listado por HTTP. Restaura PostgreSQL y cierra APIs temporales en finally.

La base aislada `hospital_v1_validation_<uuid>` se conserva como evidencia,
pertenece a hospital_dev y revoca CONNECT público. Sólo la migración usa APP_ENV
production para admitir ese nombre sin relajar las reglas de desarrollo/test;
no arranca API ni semilla en ese modo y la conexión sigue en loopback.
No representa despliegue productivo. Cada ejecución crea una base aislada adicional.

El diagnóstico registra 1.000 pacientes ficticios nuevos mediante búsqueda/alta
HTTP y los conserva en hospital_test. Realiza 10 calentamientos y 100 mediciones
por folio/nombre/TEST, concurrencia 1 y auditoría activa. El total de la base incluye
evidencia ficticia anterior; se registra junto con equipo, versión, tiempos y errores.
Repetir añade otro lote, por lo que se debe comparar también el volumen acumulado.
Resultados, muestras y limitaciones: [evidencia V1-07](evidencia/v1-07-resultados.json)
y [validación final](validacion-v1.md#v1-07--validación-y-entrega).
