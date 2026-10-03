# Contrato mínimo V1 — revisión 4

Fecha: 2026-10-02. Contrato originado en V1-01; revisión 4 documenta episodios
implementados en V1-06. Conserva pacientes y límites de búsqueda V1-05,
auditoría V1-04 e identidad local V1-03. El contrato no acredita
por sí solo implementación de todos los endpoints ni aprobación clínica institucional.
Entorno y versiones: [evidencia V1-01](evidencia-v1-01.md).
Origen: [Pacientes](requerimientos/2.%20PACIENTE.md) y
[Admisión](requerimientos/1.%20ADMISION.md). Alcance: [plan](../plans/v1-base-backend.md).

## Decisiones de implementación

Monolito modular, API `/api/v1`, SQLAlchemy síncrono con Psycopg 3 y PostgreSQL.
Rutas → servicios → persistencia; autorización explícita en servicios y rutas.
Una sesión por solicitud; cada servicio delimita la transacción. Migraciones Alembic,
sin `create_all` al arrancar. No existe entidad de expediente clínico en esta versión.

UUID v4 generado por el servidor como llave interna. Folios `PAC-000000000001` y
`EPI-000000000001`, con secuencias PostgreSQL independientes, crecientes y sin reinicio
ordinario. Doce dígitos es ancho mínimo; admitir crecimiento. UNIQUE y NOT NULL en
folios; no se garantiza continuidad sin huecos. No usar CURP ni correo como llave.
Todas las fechas de registro son `timestamptz`, generadas por servidor y expuestas
en UTC ISO 8601. La fecha de nacimiento es `date`, sin zona horaria.

## Datos y validación

Las entradas rechazan campos extra y valores de sólo lectura. No convertir cadenas
vacías en datos desconocidos: usar `null`. Recortar espacios exteriores; normalizar
texto a Unicode NFC; conservar acentos y grafía del nombre. UUID y fechas se validan;
fecha de nacimiento posterior al día UTC actual se rechaza. No calcular edad aparente.

| Paciente | Regla |
|---|---|
| `id`, `folio` | Generados; inmutables. |
| `identity_status` | `provisional` o `verified`; obligatorio en alta. No hay transiciones en V1. |
| `given_names`, `family_name`, `second_family_name` | Texto nullable de 1–100 caracteres cada uno. Sin obligación de dos apellidos. |
| `birth_date` | Fecha nullable. No inventar fecha para un desconocido. |
| `identifiers` | Lista de 0–10 pares `{system, value}`; no duplicar un par dentro de la entrada. |
| `created_at`, `created_by` | Fecha UTC y UUID del actor interno; sólo servidor. |

Provisional admite todos los datos demográficos desconocidos; un nombre conocido no
obliga a declarar identidad verificada. Verificado requiere `given_names` y el permiso
adicional `patients.verify_identity`. Es una declaración del supervisor ficticio en la
prueba, no verificación automática de documentos. No exige CURP ni nacimiento.

Catálogo inicial de identificadores: `CURP` y `TEST` (exclusivamente ficticio).
`CURP`: mayúsculas ASCII, exactamente 18 caracteres alfanuméricos; sólo validación
estructural, sin certificación ni consulta externa. `TEST`: mayúsculas ASCII,
1–64 caracteres de `[A-Z0-9_-]`. Recortar extremos y convertir a mayúsculas antes de
comparar/guardar. Ningún identificador es obligatorio. No admitir cadena vacía.
Otros documentos, pasaportes y emisores se incorporarán con contrato específico.

La pareja normalizada `(system, value)` es UNIQUE global en base, también para
provisionales: V1 reserva identificadores declarados y evita asignarlos dos veces.
Es una regla de desarrollo más estricta que comprobar sólo verificados. Un conflicto
no prueba que ambas personas sean la misma; no fusionar ni confirmar identidad.
Una urgencia sin identificación puede registrarse sin ese identificador conflictivo.
Nombre/nacimiento coincidentes son candidatos, nunca una restricción de unicidad.

| Episodio | Regla |
|---|---|
| `id`, `folio` | Generados; únicos e inmutables. |
| `patient_id` | UUID obligatorio; FK a paciente existente con `ON DELETE RESTRICT`. |
| `type` | `emergency`, `outpatient` o `inpatient`, obligatorio. Catálogo V1 limitado. |
| `status` | Sólo `open`, asignado por servidor y respaldado por CHECK. |
| `created_at`, `created_by` | Fecha UTC y UUID de actor interno; no aceptados en entrada. |

Provisional puede abrir cualquiera de estos tipos; urgencia no requiere datos
administrativos adicionales. Un paciente puede tener varios episodios abiertos,
incluido el mismo tipo. No modelar cierre, conversión, triage, servicio, cama,
cuenta, diagnóstico ni fecha clínica de ingreso. Los tipos no implementan esos flujos.

## Identidad y permisos

Usuario interno: UUID, `actor_key` único, referencia `(provider, subject)` única,
`status` (`active`/`inactive`) y roles. Roles y permisos con códigos únicos y tablas
de asignación sin duplicados y con FK. Referencia local `provider=development`.
No existe API de administración de usuarios/roles en V1; semilla idempotente.

Modo simulado: `APP_ENV=development|test` y `DEV_IDENTITY_ENABLED=true`, desactivado
por defecto. `APP_ENV=production` con bandera activa falla al iniciar. Actor resuelto
por `X-Dev-Actor`, comprobando usuario activo y permisos en base en cada solicitud.
Cabeceras de rol y actores arbitrarios no conceden acceso. Modo deshabilitado rechaza
rutas protegidas con 401 mientras no exista un proveedor real. Salud pública.
API en `127.0.0.1:8000`; PostgreSQL en `127.0.0.1:5432`, bases `hospital_dev` y
`hospital_test`. La preparación de pruebas debe rechazar una URL de la base de desarrollo.

| Permiso | admision-demo | supervisor-demo | consulta-demo |
|---|---|---|---|
| `patients.search`, `patients.read` | Sí | Sí | Sí |
| `patients.read_demographics` | Sí | Sí | No |
| `patients.create` | Sí | Sí | No |
| `patients.verify_identity` | No | Sí | No |
| `admissions.create` | Sí | Sí | No |
| `admissions.read` | Sí | Sí | Sí |
| `audit.read` | No | Sí | No |

Sembrar además `inactivo-demo` sin acceso efectivo. Roles no implican privilegios
universales: comprobar cada permiso listado. `patients.read_demographics` sólo amplía
campos; no sustituye `patients.read`/`patients.search`. Búsqueda/lectura limitada expone
`id`, `folio`, `identity_status`, `given_names`, `family_name`, `second_family_name`.
Demografía añade `birth_date`, `identifiers`, `created_at`, `created_by`. Los campos
no autorizados se omiten del JSON. Episodio expone `id`, `folio`, `patient_id`,
`type`, `status`, `created_at` y `created_by`, sin incorporar demografía ni información clínica.

Adición comprobada en V1-03: `GET /api/v1/identity/me`, protegida por actor activo,
devuelve únicamente `{id, actor_key, permissions}` del actor resuelto, con permisos
ordenados. Sin permiso de negocio adicional; sin administración de usuarios.
Es una ruta de diagnóstico local, también rechazada cuando el modo está apagado.
Pacientes y episodios se implementaron en V1-05/06; validación final pendiente de V1-07.

## Operaciones y búsqueda previa

| Método y ruta bajo `/api/v1` | Entrada y respuesta | Permiso |
|---|---|---|
| GET `/patients` | Filtros; 200 página y `search_id`. | `patients.search` |
| POST `/patients` | Datos + `search_id`; 201 paciente y `Location`. | `patients.create` y `patients.search`; permiso adicional si verificado. |
| GET `/patients/{id}` | 200 proyección del paciente. | `patients.read` |
| POST `/admissions` | `{patient_id,type}`; 201 episodio y `Location`. | `admissions.create` |
| GET `/admissions/{id}` | 200 episodio. | `admissions.read` |
| GET `/patients/{id}/admissions` | 200 página; 404 si paciente inexistente. | `admissions.read` y `patients.read` |
| GET `/audit` | Filtros `resource_id`, `action`; 200 página. | `audit.read` |
| GET `/health/live` | 200 `{status:"alive"}`, sin consultar base. | Público |
| GET `/health/ready` | SELECT 1; 200 `{status:"ready"}` o 503 genérico. | Público |

Todas las listas: `limit` 1–100 (20 por defecto), `offset` ≥0 (0 por defecto),
respuesta `{items,limit,offset,total}`. Orden estable `(created_at,id)` ascendente;
no prometer una instantánea entre páginas durante escrituras concurrentes.

Búsqueda: `folio` exacto, `name` (1–302 caracteres, subcadena literal del nombre
completo, insensible a mayúsculas y sensible a acentos), o pareja `identifier_system`
y `identifier_value` exacta normalizada. Filtros combinados con AND. `%` y `_` en
nombre son literales, no comodines. Sin filtros devolver 422, salvo
`unidentified=true`, incompatible con otros filtros: búsqueda vacía justificada
para persona totalmente desconocida, sin listar toda la base.

La búsqueda crea evidencia breve en base: UUID `search_id`, actor, filtros
normalizados, fecha y expiración a los 15 minutos. Es referencia opaca, no identidad
ni autorización. Alta requiere referencia vigente del mismo actor. Si hay identificador,
la búsqueda debe incluir uno de los pares del alta; sin identificador pero con nombre,
debe haberse buscado ese nombre completo; sin ambos debe usarse `unidentified=true`.
El resto de filtros no puede contradecir los datos enviados. Rechazar referencias
ajenas, inexistentes, vencidas o que no correspondan, sin revelar su propietario.
No exigir referencia para crear episodio de paciente ya existente.

Antes de insertar, el servicio repite detección exacta sobre TODOS los identificadores
del alta. UNIQUE decide también ante concurrencia; traducir el fallo previsto a 409.
No depender sólo del resultado de la búsqueda previa. Búsqueda puede devolver varios
candidatos; no selecciona ni fusiona automáticamente. El acuse no bloquea homónimos.
Su almacenamiento no necesita limpieza para funcionar; depuración posterior puede
borrar sólo referencias expiradas, nunca pacientes ni eventos de auditoría.

No hay PUT, PATCH ni DELETE de pacientes/episodios, ni edición/eliminación de auditoría.
Un reintento de alta sin identificadores puede crear otro provisional; V1 no promete
idempotencia HTTP de altas. Informarlo en la guía del cliente.

## Errores y auditoría

Formato único: `{error:{code,message,details},request_id}`; `details` es lista de
errores con ruta de campo y código, sin reproducir valores personales recibidos.
Generar UUID de correlación en servidor y devolver `X-Request-ID`. Nunca aceptar
fecha ni actor de auditoría del cliente. No filtrar SQL, URL de base o trazas.

| HTTP | Código | Caso |
|---|---|---|
| 401 | `IDENTITY_REQUIRED` | Actor ausente/desconocido/inactivo o modo deshabilitado; mismo mensaje. |
| 403 | `PERMISSION_DENIED` | Actor activo sin permiso; comprobar antes de leer el recurso. |
| 404 | `RESOURCE_NOT_FOUND` | UUID válido sin paciente/episodio, sólo tras autorización. |
| 409 | `IDENTIFIER_CONFLICT` | Identificador reservado, incluido conflicto concurrente; sin datos del otro paciente. |
| 422 | `VALIDATION_ERROR` | Campos, filtros, enum o UUID inválidos. |
| 422 | `SEARCH_REQUIRED` | Referencia de búsqueda inválida o incompatible. |
| 503 | `DATABASE_UNAVAILABLE` | Base inaccesible o timeout; sin credenciales. |
| 500 | `INTERNAL_ERROR` | Fallo no previsto; respuesta genérica. |

Auditoría: UUID, actor interno nullable sólo en denegación sin identidad, acción
(`patients.search/create/read`, `admissions.create/read/list`, `audit.read`, `identity.read`),
tipo/UUID de recurso nullable en búsquedas, resultado (`success`/`denied`),
fecha servidor, correlación y metadatos mínimos. Creación guarda valores nuevos
del contrato en auditoría restringida; anterior `null`. Lecturas/búsquedas no copian
nombres, filtros personales ni contenidos completos. No hay modificaciones que
requieran imágenes anteriores en V1.

Cambio y evento de éxito comparten transacción. Si falla la auditoría, no confirmar
el cambio ni devolver éxito; lecturas sensibles también fallan sin evento persistido.
Denegaciones usan transacción independiente y no almacenan detalles del paciente.
Si ese canal no está disponible, dejar log técnico mínimo de código/correlación,
sin cuerpos, parámetros, cabeceras de identidad, tokens ni datos personales.
La consulta de auditoría registra su propio acceso y no devuelve recursivamente
eventos nuevos del mismo acceso. Restringir según `audit.read`; sin prometer
protección contra un administrador PostgreSQL con permisos de escritura.

Precisiones comprobadas en V1-04: tabla `audit_events`, migración 0002. Campos
`id`, `actor_id`, `action`, `resource_type`, `resource_id`, `result`, `created_at`,
`request_id` y `metadata`. Fecha del evento con `clock_timestamp()` del servidor;
correlación UUID generada por la API. No hay FK polimórfica del recurso; el actor sí
tiene FK restrictiva. CHECK limita acciones/resultados, exige actor en éxitos y
objeto JSON en metadatos. Denegaciones sólo conservan `metadata={code}` y
`resource_id=null`; actor nullable si no se resolvió una identidad activa.

`GET /audit` admite los filtros/orden/paginación del contrato y sólo `audit.read`.
Su página y total se consultan en una sola sentencia; después guarda su evento y
confirma la transacción antes de devolver. Su propio acceso no aparece en esa
respuesta. Creaciones guardan `{old:null,new:{campos del contrato}}`, incluidos
identificadores con sólo system/value; consultas y búsquedas guardan `{}`.
Identidad local también registra `identity.read`, sin copiar permisos ni cabeceras.
No hay un endpoint para que el cliente escriba eventos.

Cada futura ruta sensible debe declarar `name` con su acción canónica; el manejador
de errores usa ese nombre para registrar 401/403 en una sesión independiente.
`record_success` exige la transacción del servicio y sólo añade/flush; no hace commit.
La integración con pacientes/episodios se comprobó en V1-05/06. V1-04 comprueba el
límite transaccional con recursos ficticios de prueba, no pacientes implementados.

## Precisiones comprobadas en V1-05

Migración 0003 crea `patients`, `patient_identifiers`, `patient_searches`, secuencia
`patient_folio_seq` y función `next_patient_folio()`. La función usa doce dígitos
como mínimo y conserva un bigint mayor; secuencia sin CYCLE, independiente de UUID.
Restricciones de identidad, nombre verificado, nacimiento, folio e identificador,
y FK restrictivas respaldan las reglas. UNIQUE global impide duplicados aun con
altas simultáneas. Conflicto esperado se traduce después de revertir la transacción.

Búsqueda crea referencia y auditoría en la misma transacción; expiración de 15 minutos
según reloj PostgreSQL. Página y total comparten sentencia. Unidentified devuelve
página vacía, incluso habiendo provisionales existentes. El alta no consume el acuse;
no se promete idempotencia sin identificadores. Se comprueban todos los identificadores.
Una búsqueda por folio sirve para seleccionar un existente, no respalda un alta nueva
cuyo folio generará el servidor. Si hay nombre adicional en los filtros, debe coincidir
con el nombre completo del alta. Referencias inválidas comparten SEARCH_REQUIRED.

Corrección de contrato: nombre de búsqueda acepta 1–302 caracteres. El rango anterior
2–300 impedía registrar el nombre válido de un carácter y el máximo válido de tres
componentes de 100 más dos separadores. Alternativa descartada: restringir los datos
del paciente para acomodar la búsqueda. Pruebas cubren ambos extremos; resto de reglas
sin cambios. Fechas ISO pueden representar UTC como Z o +00:00 (mismo instante).

## Precisiones comprobadas en V1-06

Migración 0004 crea `admissions`, `admission_folio_seq` sin CYCLE y función
`next_admission_folio()`. Folios EPI con mínimo doce dígitos y crecimiento sin
truncar. UUID y secuencia son independientes de pacientes. FK a paciente y autor
con ON DELETE RESTRICT; CHECK de tipo, estado open y formato de folio; UNIQUE
sobre folio e índice `(patient_id,created_at,id)` para listar atenciones.

POST sólo admite patient_id/type, sin búsqueda previa nueva ni datos administrativos.
Actor y fecha son del servidor. Permiso admissions.create basta para crear;
no implica permiso de lectura. GET de episodio requiere admissions.read y no entrega
campos del paciente. Listado requiere además patients.read; devuelve página vacía
para paciente existente sin episodios y 404 para paciente inexistente. Total y página
comparten sentencia; orden estable creado/id. Cada lectura/listado confirma su
auditoría antes de responder; sin datos si el registro falla.

Creación/lectura auditan tipo admissions y UUID del episodio. Listado registra
admissions.list con resource_id null y metadata vacía, conservando acción/actor/
correlación sin copiar el filtro de paciente. No emplea UUID de paciente como UUID
de episodio. Denegaciones conservan sólo código, actor cuando se resolvió y correlación.
No hay PUT/PATCH/DELETE, conversiones, cierre, camas ni cargos. Varias altas del
mismo tipo/paciente son episodios independientes, incluso simultáneas. No se promete
idempotencia HTTP; reintentar puede abrir otro episodio. Fallo de FK de paciente
entre comprobación e inserción se revierte y responde 404 controlado.

## Ejemplos exclusivamente ficticios

Búsqueda con admision-demo: `GET /api/v1/patients?identifier_system=TEST&identifier_value=DEMO-001`.
El UUID del ejemplo representa el `search_id` que realmente devuelva esa búsqueda.

```json
{
  "search_id": "9d09405e-73d9-422f-85d0-ce0484fbb2e9",
  "identity_status": "provisional",
  "given_names": "Persona de Prueba",
  "family_name": "Ficticia",
  "second_family_name": null,
  "birth_date": "1990-01-01",
  "identifiers": [{"system": "TEST", "value": "DEMO-001"}]
}
```

Desconocido: buscar `GET /api/v1/patients?unidentified=true` y usar su referencia:

```json
{
  "search_id": "69a9e459-b289-4ab2-813d-38ef0e052dc7",
  "identity_status": "provisional",
  "given_names": null,
  "family_name": null,
  "second_family_name": null,
  "birth_date": null,
  "identifiers": []
}
```

Para ambos: `POST /api/v1/admissions` con
`{"patient_id":"a6d86d83-04b9-4734-8709-c145e7e2bdea","type":"emergency"}`,
sustituyendo el UUID por el paciente devuelto. Ejemplo de conflicto:

```json
{"error":{"code":"IDENTIFIER_CONFLICT","message":"Identificador ya registrado","details":[]},"request_id":"5f114d31-da7e-4ebf-9f41-64781c14910f"}
```

## Trazabilidad y criterios de prueba

Estos casos se ejecutan en las etapas indicadas, sobre PostgreSQL cuando persisten
datos. La evidencia ejecutada se detalla en validacion-v1.md; V1-07 comprueba
infraestructura final, reinicio con pacientes/episodios y diagnóstico de rendimiento.
Ningún requisito de esta tabla se declaró implementado por el contrato de V1-01.

| Origen | Criterio de aceptación verificable | Etapa y límites |
|---|---|---|
| PAT-RF-001 | P01: dos altas tienen UUID/folios distintos; lectura conserva identidad. | V1-05; identificador interno. |
| PAT-RF-002 | P02: buscar por folio, nombre y TEST; límites, literales, AND y proyección. | V1-05; otros identificadores/contactos y fonética diferidos. |
| PAT-RF-003 | P03: alta sin búsqueda, expirada, ajena o incompatible da 422; repetido da 409. | V1-05; detección exacta parcial, sin similitud avanzada. |
| PAT-RF-004 | P04: alta sin CURP da 201 y se recupera. | V1-05. |
| PAT-RF-005 | P05: dos desconocidos sin nombre/nacimiento/identificadores dan 201 independiente. | V1-05; enriquecimiento posterior diferido. |
| ADM-RF-001 | A01: búsqueda previa genera referencia ligada al actor y alta la exige. | V1-05; sin interfaz visual. |
| ADM-RF-002 | A02: nombre devuelve varios candidatos sin fusión; TEST exacto encuentra registrado. | V1-05; advertencias sólo por resultados exactos/subcadena. |
| ADM-RF-003 | A03: un paciente admite varios episodios; FK inválida da 404 y no deja evento de éxito. | V1-06; sin flujo de admisión completo. |
| ADM-RF-004 | A04: desconocido abre emergency sin CURP/fecha; relación permanece. | V1-05/06; sin brazalete ni vinculación posterior. |
| PAT-RNF-002 | S01: consulta-demo omite nacimiento/identificadores; no crea ni lee auditoría. | V1-03/05; sin identidades protegidas avanzadas. |
| PAT-RNF-004 | S02: rollback puede dejar hueco de folio; el siguiente no lo reutiliza; UUID inmutable. | V1-05/07; sin DELETE ni reinicio de secuencias. |
| PAT-RNF-005 | S03: no existen rutas de borrado; FK impide borrar paciente con episodio. | V1-05/06; no garantiza resistencia a administrador de BD. |
| PAT-RNF-007 | S04: mismo recorrido desconocido → urgencia sin documentos, sin inventar valores. | V1-05/06. |
| ADM-RNF-001 | A05: episodio emergency sólo exige paciente y tipo. | V1-06; no completa admisión institucional. |
| ADM-RNF-004 | S05: ausente/inactivo/desconocido 401; permiso insuficiente 403 aun con UUID inexistente. | V1-03/06; permisos locales, sin autenticación real. |
| ADM-RNF-005 | S06: API sin DELETE; pacientes/episodios se conservan al reiniciar PostgreSQL. | V1-06/07; sin anulación administrativa. |
| PAT-RNF-003, auditoría V1 | T01: provocar fallo de auditoría revierte paciente/episodio y evento de éxito; denegación persiste aparte. | V1-04/07; cambios de identidad diferidos. |
| Concurrencia V1 | T02: dos conexiones/transacciones con barrera crean mismo TEST normalizado: exactamente 201 y 409, un paciente/evento de éxito. | V1-05/07; repetir con identidad verificada y supervisor. |
| Aislamiento local V1 | T03: production + bandera activa impide arranque; desactivada da 401; cabecera de rol no otorga permisos. | V1-03. |
| Integridad V1 | T04: campos extra, futuro, vacíos, tipo/estado indebidos y duplicados en entrada dan 422; base impone UNIQUE/CHECK/FK. | V1-05/06/07. |
| Infraestructura V1 | T05: migrar base vacía; ready 503 y live 200 con base caída; preparación no borra datos. | V1-02/07. |

PAT-RNF-001 y ADM-RNF-002 (gran volumen) quedan diferidos como cumplimiento.
En V1-07 medir diagnóstico local reproducible: 1.000 pacientes ficticios, 100 búsquedas
por folio/nombre/TEST cada una después de 10 de calentamiento, concurrencia 1;
registrar p50/p95/máximo, errores, equipo y configuración. No fijar SLA clínico ni
declarar rendimiento a gran escala a partir de esa medición.

Diferidos: PAT-RF-006–015 (incluido recién nacido especializado), restantes RF de
Admisión, fusiones, actualización/verificación posterior, historial de correcciones,
contactos, documentos, identidad protegida, firma, clínica, integración y frontend.
Las reglas de verificación, catálogo y reserva global se reconsiderarán antes de uso
institucional; cambios al contrato exigirán actualizar pruebas y migraciones afectadas.
