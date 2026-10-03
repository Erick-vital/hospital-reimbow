# Plan V1 — Base backend

Fecha: 2026-10-02. Estado: V1-01–07 completadas; entrega backend local validada.

## Objetivo

Construir una base backend local reproducible con FastAPI y PostgreSQL que demuestre el flujo búsqueda de paciente → registro o selección → creación de episodio → consulta autorizada, con migraciones, reglas mínimas y auditoría.

Esta versión prepara infraestructura y contratos del proyecto. No constituye un HIS completo ni una versión para operación clínica. El usuario autorizó V1-01 y después continuar con V1-02–07 el 2026-10-02. No implica despliegue ni implementación de versiones posteriores.

Referencia: [propuesta técnica](../docs/propuesta-tecninca.md). Continuación: [ESTADO.md](../ESTADO.md).

## Alcance

Incluye estructura modular; configuración por entorno; PostgreSQL; SQLAlchemy y Alembic; validación Pydantic; API `/api/v1`; comprobaciones de salud; identidad institucional y permisos mínimos; auditoría de operaciones sensibles; pacientes y episodios mínimos; datos ficticios; pruebas reproducibles y guía de uso.

Se incluirán pacientes identificados y provisionales, búsqueda previa y detección exacta de identificadores repetidos. La similitud fonética, fusiones y separaciones serán posteriores. Los tipos de episodio serán un catálogo inicial explícito, sin afirmar que sus flujos clínicos completos estén implementados.

## Fuera de V1

- Cognito, Keycloak, contraseñas propias, MFA, SSO, recuperación e invitaciones reales.
- AWS, infraestructura productiva, servicios de pago e integraciones externas.
- Frontend React; el flujo se probará mediante OpenAPI y cliente HTTP.
- Firma clínica, notas, supervisión operativa de MIP, prescripción, eMAR y Farmacia.
- Gestión de camas, traslados, aseguradoras, cuentas, caja y facturación.
- Archivos clínicos, PACS, laboratorio, HL7/FHIR, dispositivos, mensajería y colas externas.
- Soporte de decisiones clínicas, políticas regulatorias definitivas, alta disponibilidad y certificación de cumplimiento.

Estos límites son de esta versión, no eliminaciones de requerimientos del producto.

## Diseño inicial

Estructura propuesta, ajustable con motivo documentado:

```text
backend/
  pyproject.toml
  src/hospital/
    main.py
    core/                 # configuración, errores, conexión
    identity/             # usuarios institucionales y proveedor local
    authorization/        # permisos y comprobaciones
    audit/                # eventos de auditoría
    patients/             # rutas, esquemas, servicios y persistencia
    admissions/           # episodios mínimos
  migrations/
  tests/
  scripts/                # preparación local y comprobaciones
  .env.example
compose.yaml              # PostgreSQL local, si Docker está disponible
docs/desarrollo-v1.md      # se crea con comandos ya comprobados
docs/validacion-v1.md      # se crea cuando existan resultados reales
```

PostgreSQL será también el motor de las pruebas de integración. Fijar versiones y dependencias tras comprobar el entorno. Usar una sesión SQLAlchemy por solicitud/unidad de trabajo y transacciones en servicios; evitar commits dispersos que separen un cambio de su auditoría.

### Identidad de desarrollo

Crear una dependencia de identidad reemplazable por un proveedor futuro. En V1 resolverá únicamente actores ficticios predefinidos en desarrollo y pruebas, por ejemplo mediante `X-Dev-Actor`. La selección del actor permite simular permisos; **no autentica a una persona**.

- Habilitación explícita mediante entorno de desarrollo/pruebas y bandera desactivada por defecto.
- API y PostgreSQL publicados únicamente en la interfaz local para este uso.
- Actor inexistente, ausente o inactivo: rechazo; permiso insuficiente: 403.
- Con el modo local deshabilitado, rutas protegidas rechazan solicitudes sin proveedor real; salud puede seguir pública.
- Un entorno productivo configurado con el proveedor simulado debe fallar al iniciar.
- Ningún rol arbitrario recibido en una cabecera otorga permisos.
- No almacenar contraseñas ni añadir un segundo sistema de login temporal.

Guardar usuario interno, referencia de identidad, estado, roles y permisos. Cédulas, especialidad, privilegios avanzados, turnos y asignaciones se definirán cuando su flujo forme parte del alcance.

### Datos mínimos

- Usuario institucional, roles, permisos y sus asignaciones.
- Paciente: ID interno estable, folio legible único, identidad provisional/verificada, nombre y fecha de nacimiento cuando se conozcan, identificadores externos opcionales.
- Episodio: ID, folio, paciente, tipo, estado inicial y fecha real de creación.
- Auditoría: actor interno, acción, recurso, resultado, fecha del servidor y correlación; valores anteriores/nuevos cuando corresponda.

No usar CURP como llave primaria, no inventar información para completar campos y no eliminar pacientes/episodios mediante la API V1. Fechas con zona horaria y captura controlada por servidor; no confundir fecha clínica con fecha de registro en versiones futuras.

## Etapas y criterios de aceptación

### V1-01 — Entorno y contrato mínimo

- [x] Comprobar Python, PostgreSQL/Docker disponibles y estructura real del proyecto.
- [x] Fijar versiones compatibles, dependencias y forma de instalación reproducible.
- [x] Definir campos, estados, permisos y errores mínimos de Pacientes y Episodios.
- [x] Registrar cobertura parcial de los requisitos y diferidos; no equiparar número de endpoints a cumplimiento.

Entregables: [contrato revisión 1](../docs/contrato-v1.md),
[entorno y evidencia](../docs/evidencia-v1-01.md),
[lock con hashes](../backend/requirements.lock). Compatibilidad comprobada mediante
resolución para Python 3.12.3/Linux x86_64; instalación/ejecución verificadas después en V1-02.
El contrato concreta campos/estados y reemplaza la trazabilidad preliminar inferior.

Aceptación: contrato revisable con ejemplos ficticios y cada requisito seleccionado asociado a criterio de prueba. No instalar componentes del sistema ni contratar servicios por el solo hecho de planificarlos.

### V1-02 — Arranque y persistencia

Depende de V1-01.

- [x] Crear aplicación modular, configuración validada y `.env.example` sin secretos.
- [x] Preparar PostgreSQL local con volumen persistente y base de pruebas separada.
- [x] Configurar SQLAlchemy y Alembic; migración inicial reproducible.
- [x] Crear salud de proceso y disponibilidad de base diferenciadas.

Evidencia: [validación V1-02](../docs/validacion-v1.md),
[comandos comprobados](../docs/desarrollo-v1.md) y
[resultados estructurados](../docs/evidencia/v1-02-resultados.json).
26 pruebas pasan; base test inicialmente vacía migra a 0001. PostgreSQL 18.6
queda activo con volumen persistente y usuarios separados. API temporal verificada
por HTTP; base detenida da ready 503/live 200 y vuelve a 200 tras reinicio.
Esquema inicial de usuarios/roles/permisos; semilla y flujos en etapas posteriores.

Aceptación: una base vacía llega al esquema vigente mediante migraciones; la API arranca con instrucciones comprobadas; la caída de la base afecta disponibilidad sin declarar muerto el proceso ni revelar credenciales. Crear tablas al arrancar no sustituye migraciones.

### V1-03 — Identidad local y autorización

Depende de V1-02.

- [x] Sembrar actores ficticios de admisión, supervisor y consulta con permisos explícitos.
- [x] Implementar dependencia de identidad local y protección de rutas.
- [x] Definir consulta limitada y permisos de búsqueda, creación y lectura de episodios.
- [x] Probar aislamiento del modo local respecto a configuración productiva.

Evidencia: [validación V1-03](../docs/validacion-v1.md#v1-03--identidad-local-y-autorización),
[resultado estructurado](../docs/evidencia/v1-03-resultados.json) y
[guía local](../docs/desarrollo-v1.md#identidad-local-y-permisos-v1-03).
58 pruebas pasan sobre PostgreSQL: matriz completa, denegaciones, revocación y
proyecciones de campos. Semilla repetida en ambas bases conserva UUID y suspensiones.
HTTP real confirma identidad habilitada/deshabilitada y rechazo productivo.
Ruta protegida `/api/v1/identity/me`; pacientes/episodios y auditoría siguen en
sus fases. Identidad deshabilitada por defecto. No requiere nueva migración.

Aceptación: pruebas demuestran rechazo de actor ausente/inactivo, 403 sin permiso y fallo de arranque al intentar habilitar identidad simulada en producción. Los datos que devuelve cada ruta respetan su permiso.

### V1-04 — Auditoría

Depende de V1-03.

- [x] Registrar creación/consulta sensible de pacientes y episodios con actor y correlación.
- [x] Escribir cambio y auditoría de éxito en la misma transacción.
- [x] Registrar denegaciones en un canal separado de la transacción revertida.
- [x] Restringir consulta de auditoría; sin endpoints de edición o eliminación.
- [x] Excluir contraseñas, tokens y datos personales innecesarios de logs técnicos.

Evidencia: [validación V1-04](../docs/validacion-v1.md#v1-04--auditoría),
[resultados estructurados](../docs/evidencia/v1-04-resultados.json) y
[guía de auditoría](../docs/desarrollo-v1.md#auditoría-v1-04).
Migración 0002 aplicada/repetida en ambas bases y sin diferencias con modelos.
85 pruebas pasan; rollback de recurso/evento, denegación desde otra conexión
simultáneamente abierta, filtros/paginación, consulta fallida sin evento de éxito,
CHECK y logs mínimos. HTTP real verifica 401/403/200 y persistencia de eventos.

El primer punto implementa el registrador para las acciones clínicas del contrato;
se prueba con recursos ficticios transaccionales. Las rutas reales de pacientes y
episodios siguen en V1-05/06, donde se conectarán y se repetirán T01/S01/S05 sobre
esas entidades. No se declara ejecutado un flujo clínico por estas pruebas.
`/audit` e `/identity/me` ya integran auditoría. Contrato actualizado a revisión 2.

Aceptación: un fallo durante una creación revierte tanto el recurso como el evento de éxito; una denegación deja evidencia sin exponer datos del recurso. La V1 no promete resistencia frente a un administrador de base con permisos de escritura.

### V1-05 — Pacientes mínimos

Depende de V1-04.

- [x] Búsqueda paginada por folio, nombre e identificador externo.
- [x] Creación precedida por búsqueda; el servidor comprueba coincidencias exactas.
- [x] Identificador interno independiente de CURP y folio sin reutilización ordinaria.
- [x] Registro provisional de urgencias sin CURP ni fecha de nacimiento inventada.
- [x] Lectura con respuesta explícita y validación de campos/identificadores.
- [x] Restricciones transaccionales para evitar creación duplicada de identificadores verificados en solicitudes simultáneas.

Aceptación: crear y recuperar pacientes ficticios; representar datos desconocidos; distinguir una coincidencia de una confirmación de identidad; dos altas concurrentes del mismo identificador verificado producen un éxito y un conflicto controlado. No bloquear desconocidos por identificadores ausentes.

La regla exacta de duplicados de V1 es una propuesta técnica de desarrollo; los umbrales y excepciones institucionales se definirán antes de uso real.

Evidencia: [validación V1-05](../docs/validacion-v1.md#v1-05--pacientes-mínimos),
[resultados](../docs/evidencia/v1-05-resultados.json) y
[guía comprobada](../docs/desarrollo-v1.md#pacientes-mínimos-v1-05).
147 pruebas pasan. Migración 0003 aplicada/repetida en ambas bases y sin diferencias
con modelos. HTTP real comprueba búsqueda/alta/lectura/duplicados y permisos.
Barrera en dos conexiones después de detectar duplicados y antes de insertar:
201/409, un paciente y un evento, con identidad provisional y verificada.
Rollback probado ahora sobre paciente real con datos ficticios; referencia/búsqueda
atómica y lecturas fallan si no se persiste auditoría. Folios no se reutilizan tras
rollback y admiten más de doce dígitos. Contrato revisión 3 corrige búsqueda por
nombre de 2–300 a 1–302 para admitir todos los nombres válidos del alta.

### V1-06 — Episodios mínimos

Depende de V1-05.

- [x] Crear episodio asociado a paciente existente.
- [x] Consultar episodio y listar atenciones paginadas de un paciente.
- [x] Generar folio único y conservar autor/fecha de creación.
- [x] Respetar permisos y auditar operaciones.
- [x] Rechazar paciente inexistente y referencias inválidas.

Aceptación: un paciente tiene varios episodios independientes y relacionados correctamente; el registro provisional puede abrir urgencias sin documentación adicional. No implementar conversiones, cierre, camas o cargos implícitos.

Evidencia: [validación V1-06](../docs/validacion-v1.md#v1-06--episodios-mínimos),
[resultados](../docs/evidencia/v1-06-resultados.json) y
[guía](../docs/desarrollo-v1.md#episodios-mínimos-v1-06).
199 pruebas pasan. Migración 0004 aplicada/repetida en ambas bases y Alembic check
sin diferencias. Flujo HTTP completo con dos pacientes ficticios (uno desconocido),
cuatro episodios por paciente y lectura/listado paginado sin demografía.
Rollback comprobado sobre episodio/evento reales de prueba; folio no reutilizado.
FK restrictiva impide borrar paciente con episodio. Dos conexiones con barrera crean
episodios independientes del mismo tipo/paciente con UUID/folios distintos y auditoría.
401/403 antes de buscar referencias; paciente inexistente y carrera de FK dan 404.
Contrato revisión 4 documenta el comportamiento sin ampliar alcance clínico.

### V1-07 — Validación y entrega

Depende de V1-01 a V1-06.

- [x] Pruebas de servicios y de integración sobre PostgreSQL con datos ficticios.
- [x] Pruebas de restricciones, rollback y concurrencia del alcance implementado.
- [x] Migración de una base nueva y persistencia tras reiniciar PostgreSQL.
- [x] Script de preparación idempotente para desarrollo, sin borrar una base existente.
- [x] Guía comprobada de instalación, arranque, migración, prueba y recorrido HTTP.
- [x] Documentar resultados, limitaciones y cobertura en `docs/validacion-v1.md`.
- [x] Actualizar este plan y `ESTADO.md` con evidencia real.

Evidencia: [validación V1-07](../docs/validacion-v1.md#v1-07--validación-y-entrega),
[resultados](../docs/evidencia/v1-07-resultados.json),
[preparación](../backend/scripts/prepare_local.py) y
[aceptación reproducible](../backend/scripts/verify_phase7.py).
199 pruebas pasan, sin omisiones. Base nueva migra desde cero a 0004 y coincide
con modelos. Preparación repetida conserva configuración, todas las filas y secuencias.
Reinicio conserva pacientes, episodios y auditoría; mismo proceso API recupera su pool.
Diagnóstico: lote de 1.000 pacientes, 100 búsquedas medidas por criterio y diez de
calentamiento; p95 folio/nombre/TEST 10,347/15,185/10,783 ms, cero errores.
Concurrencia 1, sin SLA ni afirmación de capacidad productiva. API temporal cerrada,
PostgreSQL activo e identidad apagada por defecto. Versiones posteriores pendientes
de definición y autorización; V1 no incorpora frontend ni clínica completa.

Aceptación: otra sesión puede reproducir búsqueda → alta → episodio → consulta, comprobar 403 y auditoría. No se declara completo si faltan pruebas de integración o el modo simulado queda habilitado fuera de desarrollo.

## Trazabilidad inicial

| Requisito de origen | Cobertura V1 propuesta |
|---|---|
| PAT-RF-001, 002, 004, 005 | Identificador, búsqueda y pacientes sin CURP/desconocidos; búsqueda limitada a campos V1. |
| PAT-RF-003 | Detección exacta; similitud y revisión avanzada diferidas. |
| ADM-RF-001, 002, 003, 004 | Búsqueda, coincidencias exactas y episodios mínimos; interfaz visual diferida. |
| PAT-RNF-002, 004, 005, 007 | Permisos, identificadores estables, ausencia de eliminación ordinaria y urgencia sin CURP. |
| ADM-RNF-001, 004, 005 | Registro mínimo, permisos y conservación de pacientes/episodios. |
| Rendimiento, auditoría y concurrencia | Criterios concretos por definir en V1-01; medir lo implementado sin prometer carga productiva. |
| EHR, MED, ENF y FAR | Diseño considerado; flujos clínicos fuera de V1. |

Esta tabla conserva la selección inicial. La [matriz del contrato V1-01](../docs/contrato-v1.md) precisa criterios de prueba y diferencias frente al requisito completo.

## Riesgos y decisiones pendientes

- Identidad simulada: sólo entorno local y pruebas; no permite despliegue real.
- Duplicados: cobertura exacta inicial; fusión/separación e identidad clínica compleja diferidas.
- Estados/campos mínimos fijados en el contrato; políticas clínicas institucionales pendientes.
- PostgreSQL/Docker y versiones comprobados en V1-02; reconsiderar al actualizar dependencias.
- Datos de prueba: exclusivamente ficticios; nunca copiar expedientes reales para facilitar desarrollo.
- Autenticación futura: proveedor externo pendiente, separado del usuario interno.

## Registro de avances

2026-10-02: propuesta, plan, instrucciones y estado inicial preparados. Ninguna etapa de implementación completada. Añadir aquí hitos breves y enlaces a evidencia; los logs extensos se guardarán fuera de `ESTADO.md`.

2026-10-02: V1-01 completada por solicitud de implementación de la primera fase.
Docker/Compose disponibles y daemon accesible, sin contenedores activos. Python
3.12.3/venv comprobados. Contrato y 31 dependencias fijadas con SHA256; resolución
y dry-run del lock con hashes terminan con código 0.
[Evidencia y límites](../docs/evidencia-v1-01.md). No se instalaron paquetes backend
ni se inició PostgreSQL/API. Próxima etapa: V1-02.

2026-10-02: V1-02 completada tras autorización de continuar la fase 2.
FastAPI modular/configuración, PostgreSQL 18.6 por digest y volumen persistente,
bases/usuarios separados, SQLAlchemy y migración 0001 de identidad/permisos.
26 pruebas pasan. HTTP real durante caída: live 200/ready 503, recuperación 200;
persistencia comprobada. [Validación y límites](../docs/validacion-v1.md).
PostgreSQL queda activo; API temporal cerrada. Próxima etapa: V1-03.

2026-10-02: V1-03 completada tras solicitud de continuar la fase 3. Semilla
atómica/idempotente de cuatro actores, tres roles y ocho permisos en ambas bases;
dependencia local, autorización explícita y proyecciones limitadas. 58 pruebas
pasan; HTTP real y fábrica productiva comprobados.
[Validación y límites](../docs/validacion-v1.md#v1-03--identidad-local-y-autorización).
API temporal cerrada; identidad deshabilitada y PostgreSQL activo. Próxima: V1-04.

2026-10-02: V1-04 completada tras solicitud de continuar la fase 4. Migración 0002,
registrador de éxitos sin commit propio, canal independiente de denegaciones,
consulta auditada con permiso audit.read y logs mínimos. 85 pruebas pasan;
HTTP real y esquema de ambas bases comprobados. [Evidencia y límites](../docs/validacion-v1.md#v1-04--auditoría).
Se preservan datos/evidencia ficticios, sin endpoints de edición/borrado.
API temporal cerrada; identidad apagada por defecto. Próxima etapa V1-05.

2026-10-02: V1-05 completada tras solicitud de continuar la siguiente fase.
Pacientes, búsqueda previa ligada a actor/vigencia/datos y reserva global UNIQUE.
147 pruebas y HTTP real pasan. Migración 0003 aplicada en desarrollo/pruebas;
contrato revisión 3 corrige límites de búsqueda por nombre. [Resultados y límites](../docs/validacion-v1.md#v1-05--pacientes-mínimos).
PostgreSQL existente fue iniciado tras reinicio del equipo, sin reemplazar volumen.
API temporal cerrada; identidad apagada por defecto. Próxima etapa: V1-06.

2026-10-02: V1-06 completada tras solicitud explícita de fase 6.
Episodios mínimos, listado por paciente, permisos y auditoría atómica.
199 pruebas y recorrido HTTP pasan; ambas bases migradas a 0004 sin divergencias.
Desconocido abre urgencias sin documentación adicional; múltiples episodios y
concurrencia permitidos; FK restrictiva y rollback comprobados.
[Evidencia y límites](../docs/validacion-v1.md#v1-06--episodios-mínimos).
API temporal cerrada; PostgreSQL activo; identidad apagada por defecto.
Próxima fase: V1-07, validación/entrega y diagnóstico de rendimiento local.

2026-10-02: V1-07 completada tras solicitud de continuar la siguiente fase.
Preparación idempotente, base vacía 0001→0004, 199 pruebas y recorrido HTTP;
reinicio conserva todas las filas/secuencias y paciente/episodio/auditoría.
Diagnóstico con 1.000 pacientes ficticios y 300 búsquedas medidas sin errores,
sin extrapolar a capacidad productiva. [Entrega y limitaciones](../docs/validacion-v1.md#v1-07--validación-y-entrega).
V1 local completa; no se inicia V2 ni despliegue. Identidad apagada por defecto,
PostgreSQL activo y APIs temporales cerradas. Preparar revisión funcional con la
guía existente y definir/autorizar la siguiente versión antes de implementarla.
