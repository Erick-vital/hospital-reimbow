# Contrato V3 — revisión 1 para M3-01

Fecha: 2026-10-03. **Diseño base V3; lectura clínica V3-03 implementada, escritura V3-04–06 pendiente.**
Autorización: «comienza la primer etapa de plans/v3-expediente-basico.md».
Después, el usuario solicitó cerrar la etapa y aplazar inspección visual al final,
cuando haya funcionalidad. D01–D06 se conservan como base de diseño revisable;
no consta inspección realizada ni aprobación funcional individual de esas decisiones.
V3-03 autorizada posteriormente: «implementa V3-03»; [evidencia](evidencia-v3-03.md).
Alcance: [plan V3](../plans/v3-expediente-basico.md).
Revisión: [boceto](bocetos-v3.html), [matriz](validacion-v3.md) y
[evidencia/guion M3-01](evidencia-v3-01.md).

## 1. Decisiones revisables

| ID | Base de diseño | Consecuencia / alternativa |
|---|---|---|
| D01 | Captura directa; al dejar vacío, mostrar razón de ausencia con «No proporcionado» inicial, editable antes de confirmar. | No seleccionar «conocido». Revisar también desconocido, contacto e ingreso. Pedir siempre una razón explícita es alternativa, con más pasos. |
| D02 | Acceso demo global a información clínica ficticia para los dos actores clínicos; tablero «Atenciones abiertas». | No hay asignaciones ni «mis pacientes». Asignaciones mínimas requerirían ampliar modelo/pruebas antes del tablero. |
| D03 | Médico y Enfermería leen signos, alergias e historial de borradores; ambos registran signos y revisiones de alergias. Sólo Médico crea/edita sus notas. | Enfermería verá «Borrador no firmado», nunca una indicación ejecutable. Restringir la lectura de borradores a Médico es alternativa. |
| D04 | Presión arterial, frecuencia cardiaca/respiratoria, temperatura, SpO₂, peso y talla; contextos de presión, temperatura y oxígeno. | Glucemia, dolor/escalas, IMC calculado y alertas diferidos; sin umbrales diagnósticos. |
| D05 | Alergias referidas: sustancia, reacción con ausencia explícita, fuente y observación; cuatro estados longitudinales e historial. | Sólo alergia; intolerancias/reacciones adversas/contraindicaciones, gravedad y confirmación clínica diferidas y visibles como límite. |
| D06 | Una plantilla de nota inicial: motivo, antecedentes relevantes, exploración, valoración y plan narrativo. | Borrador parcial admisible con al menos una sección escrita; edición sólo del autor, versiones conservadas, sin firma/autoguardado. |

**V3-01 cerrada por instrucción del usuario**, registrada en la evidencia.
La revisión previa M3-01 deja de bloquear los dependientes; las decisiones se
conservan como base de trabajo y podrán ajustarse tras evaluación funcional final.
Si cambia una, actualizar contrato, diseño y matriz. El cierre no se basa en las
comprobaciones de HTML ni acredita aceptación funcional. V2 está en `cc86c8e`;
sus revisiones humanas pendientes conservan estado separado.

## 2. Formularios administrativos directos (V3-02)

Continuar usando `/api/v2` y [campos V2](campos-v2.md); no cambiar esquemas,
permisos, búsqueda, evidencia, fechas, reservas ni respuestas V1/V2. Nueva
presentación, mismo significado del cuerpo. No añadir edición de pacientes.

### Valor, ausencia y verificación

- Mostrar input/select de valor desde el principio. Un valor válido genera
  `known`; un valor inválido muestra error y bloquea confirmación, sin convertirlo
  en ausencia. No mostrar selector de disponibilidad si hay valor.
- Si está vacío, mostrar razón debajo: `unknown` = desconocido,
  `not_provided` = no proporcionado, `not_applicable` = no aplica cuando corresponda.
  Inicialmente `not_provided`, mostrado y revisable; no elegir `unknown` en silencio.
- Al escribir, guardar la última razón en el borrador y ocultarla. Al borrar,
  restaurarla. Antes de confirmar, normalizar NFC/extremos; sólo espacios cuentan
  como vacío y vuelven a mostrar razón. Nunca enviar `known` con `null` o `""`.
- Nombres/nacimiento conservan tipo V2 más `identity_field_states`; nuevos campos
  usan `{state,value}`. Ausencias envían `null`; no enviar etiquetas como valores.
- `known` no modifica `identity_status`. Alta provisional inicial; verificación
  es una acción aparte con permiso/evidencia V2 sobre los valores vigentes.
- Opciones pertinentes limitan captura nueva en la interfaz; el servidor V2
  sigue admitiendo sus estados existentes. Una razón histórica de API se muestra
  literalmente al revisar, incluso si no está entre las opciones nuevas. Nunca
  reclasificarla silenciosamente. No inferir nacimiento desde una edad estimada.

| Campos de captura | Razones ofrecidas si vacíos | Regla del valor / dependencia |
|---|---|---|
| Nombre(s), primer apellido | Desconocido / no proporcionado | 1–100 cada uno, opcionales para provisional. |
| Segundo apellido | Desconocido / no proporcionado / no aplica | 1–100; no deducir existencia de otro apellido. |
| Nacimiento | Desconocido / no proporcionado | Fecha de calendario no futura, sin edad fabricada. |
| Sexo registrado, nacionalidad | Desconocido / no proporcionado | Texto 1–100; sin deducción desde nombre/CURP. |
| Identificadores | Sin fila no se declaró identificador | Añadir filas CURP/TEST con reglas V2, máximo 10; sin nuevo estado de ausencia para esta lista V1. TEST sólo ficticio. |
| Teléfonos, domicilios, contactos | Desconocido / no proporcionado; acción separada «Ninguno declarado» | 0–10, al añadir fila válida → known; «Ninguno declarado» → known/[]; nunca concluir known/[] por dejar la lista vacía. |
| Relación y teléfono del contacto | Desconocido / no proporcionado / no aplica | Nombre 1–200 requerido en cada fila; relación 1–100, teléfono 1–40. |
| Componentes del domicilio | Opcionales, null sin estado individual en V2 | Tipo requerido; al menos un componente. 1–200; postal 1–20, referencias 1–500. Mantener esta limitación del esquema. |
| Desconocido: sexo aparente, edad estimada, características, procedencia, traslado | Desconocido / no proporcionado | Límites V2: 100, rango entero 0–150, 1000, 200, 200; todos opcionales. |
| Ingreso: fecha/hora, sede, servicio | Desconocido / no proporcionado sólo en urgencias | Consulta/hospitalización exigen conocidos; hora con zona, no futura; servicio de sede activa. |
| Ingreso: procedencia, motivo referido | Desconocido / no proporcionado | 1–200 / 1–1000; no se transforman en diagnóstico ni nota. |

Añadir fila crea borrador incompleto, no una lista válida. Quitar última fila vuelve
a razón previa, salvo declaración explícita «Ninguno declarado». Cambiar esa
declaración por «Añadir» la retira. Descartar filas con contenido requiere acción
explícita; revisar elementos antes de confirmar. Quitar filas sólo afecta borrador.

`is_unidentified` sigue siendo elección explícita. Activarla con identidad escrita
pide confirmar descarte y limpia nombre/nacimiento/identificadores/verificación;
conserva perfil permitido. Búsqueda previa `unidentified=true`, descriptores
opcionales. Desactivarla pide confirmar descarte de descriptores; no los convierte
en identidad. Cambio de identidad invalida búsqueda/evidencia según V2.

Confirmación resume cada valor y cada ausencia, paciente/folio y tipo de episodio.
Fecha/hora local muestra zona y offset; vacío no se llena con «ahora». Acción
«Usar hora actual» explícita permite revisarla. Cambiar sede descarta servicio con
aviso y lo exige de nuevo si corresponde. Conservar permiso de alta/verificación,
foco/teclado y protocolo V2 de intención congelada, 409/422 y respuesta perdida.

## 3. Autorización y proyección clínica

Actores propuestos `medico-demo` y `enfermeria-demo`, UUID internos estables de
la semilla, sin contraseñas. Identidad demo existente sólo con habilitación explícita
development/test; rechazar producción, inactivos y modo apagado. La semilla debe
conservar suspensiones/configuraciones y ser idempotente.

**Riesgo identificado en V3-01 y corregido en V3-03:** `identity/seed.py` definía Admisión a partir de
`PERMISSIONS - {...}` y Supervisor como `PERMISSIONS`. V3-03 fija listas explícitas: siete permisos administrativos para Admisión y
nueve para Supervisor. Ningún permiso clínico se hereda. Semilla repetida y API
con actores antiguos/nuevos comprobadas en la evidencia V3-03; se conservan
UUID, suspensiones, revocaciones de permisos y asignaciones. Supervisor conserva auditoría de metadatos; ésta no revela texto
clínico, alergias ni valores de signos.

| Permiso nuevo | Médico | Enfermería | Uso |
|---|---|---|---|
| `clinical.attentions.read` | Sí | Sí | Lista abierta y episodios longitudinales. |
| `clinical.context.read` | Sí | Sí | Cabecera/contexto por paciente/episodio. |
| `clinical.catalogs.read` | Sí | Sí | Sedes/servicios activos para filtros; no crear ingreso. |
| `clinical.vitals.read` / `clinical.vitals.create` | Ambos | Ambos | Historial/detalle / añadir medición. |
| `clinical.allergies.read` / `clinical.allergies.write` | Ambos | Ambos | Estado/historial / registrar revisión. |
| `clinical.notes.read` | Sí | Sí | Borradores y versiones de cualquier autor clínico demo. |
| `clinical.notes.create` / `clinical.notes.update_own` | Ambos | No | Crear nota / editar únicamente propia. |

En V3-03 sólo se habilitan los tres primeros permisos de lectura. Los permisos
de signos/alergias/notas de la tabla son contrato futuro de V3-04–06.

Administrativos, `consulta-demo` e `inactivo-demo`: **ninguno** de estos permisos.
Roles clínicos reciben además sólo `patients.read` y `admissions.read` existentes:
no alta/búsqueda administrativa, demografía, intake completo, verificación ni
auditoría. Todo endpoint exige ambos permisos básicos y `clinical.context.read`,
más su permiso de operación de la tabla; los de catálogo exigen contexto/catálogos,
sin permisos básicos de recurso. Comprobar en servicios y rutas, también por URL
directa, mutación y replay. Editar nota ajena → 403 con update_own, no conceder por rol.

Proyección clínica dedicada con listas de campos; no devolver ORM/perfil/intake
completos. Cabecera: UUID/folio PAC, nombres disponibles, estado/calidad de identidad;
episodio UUID/EPI, tipo, estado, fecha efectiva de ingreso y sede/servicio con sus
razones y nombres autorizados. Estos tres datos de ingreso se conceden mediante
`clinical.context.read`, exclusivamente en API clínica. No concede
`admissions.read_intake`; omitir procedencia y motivo administrativo. Sin nacimiento,
CURP, contactos, descriptores, documentos o evidencia con roles propuestos.
No añadir edad/cama/equipo inventados. `created_at` del episodio se rotula fecha
de registro; ingreso pendiente no se sustituye por esa fecha.

Los resúmenes de signos/alergias/notas sólo aparecen con su permiso de lectura;
sin él, omitir la sección y anunciar acceso no disponible, no estado «sin datos».
Ningún nombre del actor externo sustituye al UUID de autor; respuestas de autoría
usan `{id, label}` del catálogo de usuarios demo, no correo/subject/tokens.

Formas exactas comunes: `ClinicalPatient` contiene id, folio, given_names,
family_name, second_family_name, identity_status y verification_quality V2;
`ClinicalEpisode` contiene id, folio, patient_id, type, status, created_at,
admitted_at, site y service. admitted_at conserva `{state,value}` V2; site/service
son `{state,value}` con value `{id,code,name}` o null según ausencia. `legacy`
sin intake se proyecta not_provided, sin fechas/nombres inventados. created_by y
otros campos administrativos no se incorporan a esta proyección.

## 4. API clínica propuesta

Prefijo nuevo `/api/v3/clinical`. Administración conserva `/api/v2`. UUID canónicos
de paciente/episodio en rutas, no nombres ni información clínica en URL. Listados
`{items,limit,offset,total}`, limit 20 por defecto, 1–100, offset entero ≥0.
No usar `search_id` ni búsqueda previa administrativa para registrar datos clínicos.

| Método y ruta relativa | Entrada adicional | Salida / permiso de operación |
|---|---|---|
| GET `/catalogs/sites` y `/catalogs/services` | services exige `site_id` activo; paginación | `{id,code,name}`; servicios añaden site_id / catalogs.read. |
| GET `/attentions` | type emergency/outpatient/inpatient, site_id, service_id opcionales; paginación | Sólo open; cada fila `{patient,episode}` con proyección §3 / attentions.read. |
| GET `/patients/{p}/attentions` | Paginación | Episodios de ese paciente, misma proyección / attentions.read. |
| GET `/attentions/{e}/context` | — | `{patient,episode}` y secciones legibles / context.read más permisos de cada sección. |
| GET `/patients/{p}/context` | — | `{patient}` y resumen longitudinal legible / context.read más permisos de cada sección. |
| GET / POST `/attentions/{e}/vitals` | Paginación GET / cuerpo §5 POST | Lista / registro inmutable; vitals.read / vitals.create. |
| GET `/attentions/{e}/vitals/{v}` | — | Registro completo, comprobar pertenencia / vitals.read. |
| GET / PUT `/patients/{p}/allergies` | Cuerpo §6 PUT | Estado actual / nueva revisión; allergies.read / allergies.write. |
| GET `/patients/{p}/allergies/versions` | Paginación | Revisiones completas / allergies.read. |
| GET / POST `/attentions/{e}/notes` | Paginación GET / cuerpo §7 POST | Resúmenes / nota con primera versión; notes.read / notes.create. |
| GET / PUT `/attentions/{e}/notes/{n}` | Cuerpo §7 PUT | Última versión / nueva versión; notes.read / notes.update_own. |
| GET `/attentions/{e}/notes/{n}/versions` | Paginación | Versiones completas conservadas / notes.read. |

Lista abierta ordenada `episode.created_at DESC, episode.id DESC`; filtro por
service_id exige site_id y pareja coherente. Filtrar sede/servicio excluye filas
sin ese dato conocido; opción «Todas» las incluye y muestra pendiente. Catálogos
suspendidos no se ofrecen como filtros nuevos; nombres históricos se conservan en
contexto sin inventarlos. Una pareja inválida → 422; catálogo inexistente → 404.
No hay filtros por diagnóstico, turno, cama ni asignado. V3 no cierra episodios.

En V3-03 el contexto sólo devuelve identificación/episodio; el longitudinal
añade la página de episodios si hay attentions.read. No emite claves clínicas
ni estados vacíos de módulos aún no implementados. La especificación siguiente
se aplicará al implementar V3-04–06.

Contexto incluye estado actual de alergias, último registro de signos del episodio
y página inicial de resúmenes de notas; cada sección indica total y acceso a historial.
Vista longitudinal agrupa signos/notas **por episodio**, sin mezclar mediciones en
una gráfica. «Último registro de esta atención» siempre incluye fecha clínica,
captura, contexto y autor; no se rotula «actual». Si faltan lecturas, sección omitida.
Un registro ajeno al episodio de la ruta → 404 sin revelar otro contexto.

GET contexto por episodio devuelve `patient:ClinicalPatient`,
`episode:ClinicalEpisode` y claves opcionales `allergies` (revisión actual §6),
`vitals:{latest:registro§5|null,total:entero}` y `notes:páginaDeResúmenes§7`.
Vacío autorizado: vitals.latest null/total 0, notes.items []/total 0 y allergies
not_documented/version 0. Contexto longitudinal devuelve patient/allergies y
`attentions:páginaDeContextosPorEpisodio`, sólo con attentions.read; cada elemento
tiene episode/vitals/notes según los mismos permisos y estados vacíos. Esta primera
página no es todo el historial: su total y enlaces llevan a endpoints paginados.

## 5. Signos vitales

Cuerpo POST: `{patient_id, measured_at, measurements, context, observation}`.
patient_id UUID debe coincidir con episodio. measured_at ISO 8601 con offset
obligatorio, no futuro según servidor; UTC en PostgreSQL, fecha clínica distinta
de created_at. Si ingreso es conocido, no admitir measured_at anterior: 422.
Si ingreso está ausente, no fabricar una fecha mínima. Fecha clínica obligatoria
para captura; si no se conoce, conservar formulario sin guardar medición.

measurements contiene cada clave de la tabla con `{value,unit}` o null. Omitida
equivale a null = **no medido en este registro**; no significa resultado normal,
negativo, desconocido global o cero. Al menos una medición válida. Presión exige
sus dos valores juntos. No convertir unidades ni calcular valores automáticamente.

| Clave | Valor / unidad exacta | Contexto |
|---|---|---|
| `blood_pressure` | `{systolic,diastolic,unit:"mmHg"}` | position sitting/supine/standing/unknown/not_recorded; arm left/right/other/unknown/not_recorded. |
| `heart_rate` | Entero ≥0 / `beats/min` (lpm en UI) | Observación opcional. |
| `respiratory_rate` | Entero ≥0 / `breaths/min` (rpm en UI) | Observación opcional. |
| `temperature` | Decimal / `Cel` (°C en UI) | temperature_site axillary/oral/tympanic/rectal/other/unknown/not_recorded. |
| `spo2` | Decimal 0–100 / `%` | oxygen state obligatorio: room_air, supplemental, unknown o not_recorded. |
| `weight` | Decimal ≥0 / `kg` | Observación opcional. |
| `height` | Decimal ≥0 / `cm` | Observación opcional. |

Valores JSON numéricos finitos, sin cadenas/booleanos; hasta dos decimales (FC/FR
sin decimales). Capacidad técnica `numeric(7,2)`, enteros máximo 99999; presión
decimal ≥0 y Celsius admite signo. Estos límites son de representación, **no rangos
clínicos ni criterio de normalidad**. 0 informado es valor explícito; input vacío
es null. No imponer sistólica > diastólica como diagnóstico ni marcar alertas.

context usa `position`/`arm` si presión y `temperature_site` si temperatura:
requiere elección, incluidos unknown/not_recorded, no inferir método. oxygen si SpO₂:
room_air exige device/flow null; supplemental exige device 1–100 y
`flow_l_min:{state,value}` (known decimal ≥0 o unknown/not_recorded con null);
unknown/not_recorded exige device/flow null. Sin SpO₂, oxygen null; sin la medición
correspondiente, sus contextos null. method y device de equipo de medición son textos
opcionales 1–100; observation null o 1–1000. No es prescripción/administración de O₂.
No copiar contexto entre registros. Contextos unknown = no se conoce;
not_recorded = no se documentó. Ninguno afirma ausencia de soporte de oxígeno.

Salida: `{id,patient_id,episode_id,measured_at,measurements,context,observation,
created_at,created_by}`. Historial ordenado measured_at DESC, created_at DESC, id DESC.
Gráfica básica por clave/unidad/episodio, con fecha/contexto en detalle; sólo puntos
con valor, sin unir huecos como ceros ni interpolar/cambiar unidades. No editar ni
borrar. Corrección/anulación permanece deshabilitada hasta contrato propio; no
sobrescribir ni simular una corrección creando un reemplazo oculto.

## 6. Alergias longitudinales

Sin registro persistido: `{patient_id,state:"not_documented",version:0,items:[],
reviewed_at:null,created_at:null,created_by:null}`. Proyección virtual, no revisión
fabricada. PUT no admite not_documented para borrar historial; estados de nueva
revisión: unknown, no_known_allergies, recorded. unknown = se documentó que no se
conoce; no_known_allergies = declaración explícita de fuente; recorded exige 1–20
elementos. Estados sin elementos exigen []; lista vacía por sí sola no cambia estado.

Cuerpo PUT: `{expected_version,state,reviewed_at,source,items,change_reason}`.
expected_version entero ≥0; reviewed_at fecha clínica con offset no futura, sin
exigir fecha de inicio del episodio (información longitudinal). source obligatorio
en toda declaración: `{kind,reference}`; kind patient/family/document/clinical_staff/
unknown, reference null o texto 1–200; document y clinical_staff exigen referencia
descriptiva ficticia sin identificadores sensibles. unknown no afirma verificación.
change_reason texto 1–500 obligatorio en toda revisión, incluso inicial.

Elemento: `{id?,substance,reaction,source,observation}`. id UUID de elemento existente
del paciente o ausente para nuevo; servidor genera UUID, rechaza ID ajeno/repetido.
substance 1–200; reaction `{state,value}` conocido (texto 1–500), unknown o
not_provided con null. source igual al anterior, obligatorio por elemento;
observation null o 1–1000. Sólo alergias referidas; no inferir confirmación desde
fuente, no hay severidad/calificación de riesgo ni selección de fármacos.
La UI rotula «Alergias referidas · sin verificación clínica implementada».

PUT reemplaza la **instantánea vigente** por una nueva revisión completa; todo
lo anterior se conserva. Retirar un elemento o cambiar a no_known_allergies exige
confirmación y motivo; no borra historia ni marca alergia como resuelta. Lectura
informa nueva declaración y ofrece versiones previas, incluidas sustancias retiradas.
No usar DELETE. Todos los episodios leen el mismo patient_id; ningún snapshot
clínico separado por rol o episodio. Versiones inmutables 1,2,... con autor/fechas
del servidor. Actualizar cabecera tras cambio confirmado o al recuperar contexto.

Salida actual y versiones: `{patient_id,version,state,reviewed_at,source,items,
change_reason,created_at,created_by}`. Dos PUT con expected_version igual y distintas
intenciones sólo permiten uno: comparación y cambio atómicos sobre PostgreSQL,
409 VERSION_CONFLICT para el otro. La primera revisión también protege version 0
con unicidad de cabecera por paciente; no confiar en fila ausente/SELECT previo.

## 7. Nota inicial en borrador

Plantilla fija `initial_note`, versión 1. Cuerpo POST:
`{patient_id,template_code,template_version,clinical_at,sections}`.
patient_id debe coincidir; clinical_at ISO con offset no futuro y no anterior a
ingreso conocido. sections contiene `reason`, `relevant_history`, `examination`,
`assessment`, `narrative_plan`: null = sección aún no escrita, no «sin antecedentes».
Cada texto normalizado NFC/extremos 1–4000; máximo conjunto 20000 y al menos uno
escrito; omitido equivale a null. Texto simple, sin HTML/Markdown ejecutable; render
como texto. Borrador parcial admisible; jamás rellenar desde motivo administrativo,
alergias, nota anterior o mediciones. Sin dictado/IA/autoguardado en esta versión.

PUT: `{expected_version,clinical_at,sections,change_reason}`; todos completos,
sin PATCH implícito; version entero ≥1 y motivo 1–500. patient/episode/template/
author_id/state no editables, campos extra → 422. Sólo autor con update_own;
otra identidad médica puede leer pero no editar. La concurrencia se prueba también
con dos pestañas/conexiones del mismo autor, no requiere inventar supervisor.

Salida `{id,patient_id,episode_id,state:"draft",template_code,template_version,
author,created_at,version,clinical_at,sections,modified_at,modified_by,change_reason}`;
versión inicial 1, modified_by = author, change_reason null inicialmente. Versiones
siguientes conservan instantánea completa, modified_at/by, clinical_at y motivo;
created_at/author originales no cambian. Resúmenes no incluyen secciones: id,
estado/plantilla, autor, fechas/version; detalle e historial sólo con notes.read.
Orden de lista clinical_at DESC, created_at DESC, id DESC; versiones DESC.

Botones «Guardar borrador», «Guardar nueva versión», «Consultar versiones».
Etiqueta **«Borrador no firmado»** permanente en lista/detalle/confirmación.
Sin firmar/enviar/aprobar/publicar, borrar, adenda, órdenes, diagnóstico activo o
acción terapéutica. Texto de plan no alimenta otros módulos. No hay firmante ni
supervisor implícitos; ninguna fecha de firma fabricada.

## 8. Fechas, idempotencia, concurrencia y auditoría

Todo texto se normaliza como V2, salvo saltos interiores de notas que se conservan;
todo input rechaza campos extra. Fechas de autoría/captura del servidor UTC, distintas
de clinical_at/measured_at/reviewed_at; el cliente no elige created_by/modified_by.
Mostrar zona local y offset junto a fecha clínica; conservar el instante UTC.

Cada POST/PUT clínico exige Idempotency-Key UUID v4 canónico; espacio por actor,
operación versionada y recurso de ruta. Huella incorpora ruta/patient_id, todos los
valores/contextos/ausencias/fechas, expected_version y motivos normalizados. No
reutilizar sin cambios `execute_create`: actualmente sólo enlaza paciente/episodio.
Modelo/reserva V3 deben enlazar **registro clínico o revisión exacta**, con FK,
sin confundirlo con la atención. Diseño técnico que deberá comprobarse en V3-04–06.

POST inicial → 201 con Location de detalle; PUT nueva revisión → 200. Ambos:
Idempotency-Replayed false y Expires-At. Replay → 200, misma revisión, originales
de autoría/fecha y cabecera Replayed true. Una edición posterior no cambia el
resultado histórico del intento; informar número de versión y permitir «Ver vigente».
Garantía 24 h desde commit PostgreSQL; reserva vencida indefinida sin reutilizar,
espera 5 s y restauración de parámetros como V2. No renovar plazo por replay.

Orden: validar identidad/permisos/autoría y estructura → reserva → si replay,
proyectar revisión original autorizada sin comparar otra vez expected_version/fecha
de ingreso mutable → si nuevo, comprobar contexto/fecha/versión y crear revisión →
auditar → commit → responder. Revocación devuelve 401/403 sin revelar resultado.
Una nueva intención con versión obsoleta da VERSION_CONFLICT; reintento de edición
ya confirmada devuelve esa revisión, no conflicto por su propio incremento.
Distintas intenciones con expected_version igual se resuelven con comparación
atómica; UNIQUE por recurso/version y FK paciente/episodio restrictivas. Reserva,
datos y éxito de auditoría comparten transacción. Fallo de auditoría revierte todo.

Auditar lecturas clínicas, altas/revisiones, replay y denegaciones con acciones
explícitas por módulo; éxito de lectura debe confirmarse con su evento antes de
responder. Metadatos sólo recurso/episodio/paciente UUID, versión y código de
resultado; sin texto clínico, valores, nombres, clave/cuerpo/huella en logs ni en
auditoría consultable administrativa. Correlación X-Request-ID existente. Acciones
nuevas requieren migración de CHECK, pruebas de rollback y denegación sin datos.

## 9. Errores y recuperación

Envoltura V1/V2 `{error:{code,message,details},request_id}`; details sólo ruta del
campo/código, sin valor recibido. Cabeceras no-store y X-Request-ID existentes.

| HTTP / código | Regla y respuesta de interfaz |
|---|---|
| 401 (códigos de identidad existentes) | Modo apagado/actor no válido; limpiar contexto y resolver identidad. |
| 403 PERMISSION_DENIED | Permiso/autoría insuficientes antes de revelar recurso; limpiar datos afectados/revalidar. |
| 404 RESOURCE_NOT_FOUND | Recurso inexistente o dato no pertenece al contexto; sin información ajena. |
| 422 VALIDATION_ERROR | Campo, unidad, fecha, ausencia o cuerpo incoherente; conservar borrador y enfocar error. |
| 409 CONTEXT_CONFLICT | patient_id no coincide con episodio; detener captura, recargar contexto. |
| 409 VERSION_CONFLICT | Nueva edición perdió concurrencia; conservar borrador en memoria, cargar vigente mediante lectura explícita y comparar; no fusionar/sobrescribir automáticamente. |
| 409 IDEMPOTENCY_CONFLICT | Misma clave con otra intención; reconciliar, no generar nueva clave automáticamente. |
| 409 IDEMPOTENCY_IN_PROGRESS | Resultado incierto; Retry-After 1, ofrecer mismo cuerpo/clave. |
| 409 IDEMPOTENCY_EXPIRED | Consultar historial/reconciliar antes de nueva captura. |
| 500/503, timeout/red | Puede haber commit; congelar intención, sin autoenvío; ofrecer reintento explícito. |

Ante VERSION_CONFLICT confirmado, el usuario puede copiar manualmente secciones
tras comparar y confirmar nueva intención con versión vigente/nueva clave. Si hay
incertidumbre, primero resolver el intento congelado; no habilitar comparación que
lo edite. Aviso de recarga: borradores/claves se perdieron; consultar historial sin
reenvío automático. La lectura facilita reconciliar pero no garantiza identificar
por sí sola cada captura perdida. Correlación se muestra sólo si se recibió.

## 10. Navegación, almacenamiento y aceptación

Rutas frontend propuestas `/clinical/attentions`, `/clinical/attentions/:e`,
`/clinical/patients/:p`; secciones signos/alergias/notas dentro del contexto
resuelto. Cabecera PAC/EPI persistente, etiqueta longitudinal sin EPI seleccionado.
Al cambiar actor/paciente/episodio: cancelar/despreciar solicitudes anteriores por
generación, limpiar resultados/borradores/intenciones antes de resolver nuevo
contexto. Si hay texto no enviado, confirmar descarte explícito; cambio de actor
limpia inmediatamente por permisos y avisa. No arrastrar una nota del episodio A
al B aun con el mismo paciente. Atrás/pageshow/recarga vuelven a validar identidad.

Sólo memoria, sin datos clínicos en URL/storage/IndexedDB/Cache API/service worker/
consola/traces/HAR; fetch no-store. Formularios con etiquetas, unidades, contexto,
resumen de errores y foco al cambiar vista. Cabecera móvil legible; ausencia de
datos o acceso diferenciada. Boceto local sólo simula, no prueba estas garantías.

Aceptación técnica/funcional por etapa en [validación V3](validacion-v3.md).
M3-01 se aplaza por instrucción del usuario: no es requisito previo a V3-02 ni a
los demás dependientes. M3-02 valida el recorrido implementado e incluye inspección
visual de formularios/vistas y revisión de D01–D06. Aprobación final pendiente.
No afirmar expediente completo, conformidad normativa ni aptitud productiva.

## 11. Fuentes y cobertura

Fuentes locales revisadas: [Pacientes §5–10/13](requerimientos/2.%20PACIENTE.md),
[Admisión §8–11](requerimientos/1.%20ADMISION.md),
[Médico §27–29](requerimientos/4.%20MEDICO.md),
[Enfermería §10–11](requerimientos/5.%20ENFERMERIA.md),
[Expediente §4–7/12–15/23 y RF-001/002/003/004/008/010/019/020](requerimientos/3.%20EXPEDIENTE%20CLINICO.md),
y [propuesta §8.1–8.2](propuesta-tecninca.md). No se modifican originales.
Catálogos, límites de texto/capacidad, roles demo, TTL y plantilla son decisiones
del MVP propuesto, no reglas clínicas extraídas de esos documentos. Cobertura
parcial y diferidos trazados en la matriz; no se seleccionan nuevas librerías ni
estándares de interoperabilidad en V3-01.
