# Campos V2 — ampliación administrativa aprobada

Fecha: 2026-10-03. El usuario aprobó ampliar V2 con «ok hazlo entonces» tras la
recomendación de incorporar identificación, contactos, caracterización del
desconocido, ingreso administrativo y reglas de verificación. Este documento
concreta esa decisión. Backend administrativo/lecturas implementados y comprobados
en [V2-02A](evidencia-v2-02a.md); POST V2/idempotencia y frontend pendientes.
Origen: [Pacientes](requerimientos/2.%20PACIENTE.md),
[Admisión](requerimientos/1.%20ADMISION.md) y [propuesta técnica](propuesta-tecninca.md).

## Datos ausentes y calidad

En los formularios se distingue valor disponible, desconocido, no proporcionado
y no aplica. «Pendiente de verificar» es calidad de un valor disponible, no una
quinta forma de ausencia. Un campo restringido por permisos no se representa como
desconocido; se omite. No inferir sexo, nacionalidad, nacimiento o edad desde otros
datos; no sustituir desconocidos con etiquetas, ceros o fechas aproximadas.

En el contrato ampliado, campos nuevos usan `{state,value}`:
`known` exige valor válido; `unknown`, `not_provided` y `not_applicable` exigen null.
Omitir un campo nuevo equivale a `{state:"not_provided",value:null}`. `known` no
significa verificado. Para listas, `known` con `[]` significa explícitamente que no
se declaró ningún elemento; no equivale a desconocido. Los nombres/nacimiento V1
mantienen sus tipos; `identity_field_states` acompaña ausencias con las mismas
razones y rechaza contradicciones (valor no null exige known). Lista de identificadores
conserva formato V1; nunca usar TEST como evidencia de identidad real.

Texto: NFC, extremos recortados, sin cadenas vacías; no validar teléfonos como
documentos de identidad ni convertir nacionalidad a país de nacimiento.
Los límites de longitud son decisiones de implementación, no requisitos institucionales.

## Paciente

Nombre(s), apellidos, nacimiento e identificadores V1 se conservan. Ninguno es
obligatorio para alta provisional; declarar verified requiere las reglas siguientes.
Los nuevos campos se agrupan en `administrative_profile` para entrada/lectura V2.

| Campo | Contenido y validación | Ausencia |
|---|---|---|
| `registered_sex` | Sexo registrado según fuente, texto 1–100; no deducirlo de CURP/nombre ni confundirlo con sexo aparente. Catálogo institucional diferido. | Permitida. |
| `nationality` | Nacionalidad declarada, texto 1–100; sin imponer nacionalidad mexicana ni confundir con residencia. | Permitida. |
| `phones` | Lista 0–10 de `{kind,number}`; kind personal/fixed/work/other, número como texto 1–40 conservando prefijo/extensión. No llamadas/SMS ni validación externa. | Permitida. |
| `addresses` | Lista 0–10; kind principal/temporary/fiscal/correspondence/other; calle, exterior, interior, colonia, código postal, municipio, estado, país y referencias como campos opcionales. Al menos un componente no vacío por domicilio. | Permitida; no exigir domicilio mexicano. |
| `emergency_contacts` | Lista 0–10; nombre, relación y teléfono. Nombre requerido por elemento; relación/teléfono pueden quedar pendientes con su razón. No implica representación legal, obligación de pago ni autorización para información clínica. | Permitida. |

Componentes de domicilio: 1–200 caracteres excepto código postal (1–20) y referencias
(1–500); no imponer cinco dígitos a domicilios extranjeros. Nombre de contacto 1–200,
relación 1–100. No agregar un contacto ficticio para satisfacer el formulario.
La interfaz permite añadir/quitar elementos del borrador antes de confirmar; no
equivale a editar un paciente ya creado. Contactos fiscales/legales, correo, preferencias
de mensajería, documentos y fotografía siguen diferidos.

Permiso `patients.read_demographics` protege administrative_profile, descripción
del desconocido, razones de ausencia y evidencia de verificación. La proyección básica
sólo añade una señal no sensible de calidad de verificación, sin fuentes ni documentos.
Nuevos campos no se agregan a filtros de búsqueda: filtros V1 siguen siendo el límite.

## Identidad desconocida

Entrada explícita `is_unidentified=true`, provisional; nombres, nacimiento e
identificadores de identidad deben estar ausentes. Datos administrativos y
descriptivos conocidos se permiten. Buscar previamente con unidentified=true.
No derivar is_unidentified sólo por falta de nombre: una persona parcialmente
identificada no es necesariamente completamente desconocida.

`unidentified_description` contiene campos `{state,value}` opcionales:

| Campo | Contenido |
|---|---|
| `apparent_sex` | Descripción aparente, texto 1–100, distinta de sexo registrado. |
| `estimated_age` | `{min_years,max_years}`, enteros 0–150, mínimo ≤ máximo. Rango estimado, nunca fecha de nacimiento; límite técnico revisable. |
| `identifying_features` | Descripción 1–1000, sin inventar características. |
| `origin` | Procedencia conocida, texto 1–200. |
| `transferred_by` | Persona, autoridad, servicio o ambulancia que realizó el traslado, texto 1–200. |

No se exige ningún descriptor para recibir a un desconocido; se muestran pendientes.
La procedencia/traslado del episodio describe ese ingreso; el descriptor del paciente
conserva lo conocido al registro inicial. La interfaz puede copiarlo al borrador del
episodio sólo mediante acción explícita, nunca sincronizarlo o sobrescribirlo en silencio.
Pertenencias, fotografía, brazalete y enriquecimiento/fusión posteriores quedan diferidos.
No se afirma cobertura completa de Pacientes §13 ni Admisión §9.

## Verificación de identidad

En altas V2, verified exige `patients.verify_identity` y evidencia estructurada:

- Nombre completo contrastado y, al menos, fecha de nacimiento o CURP contrastada;
  dos identificadores distintos. Nombre(s)/apellidos cuentan juntos como uno.
- Campos presentes en la misma intención de alta y valores exactos normalizados;
  no bastan el folio recién generado, TEST, cama, sexo aparente o edad estimada.
- Fuente para cada identificador: documento oficial o documento institucional de
  identificación. Dos campos pueden contrastarse en el mismo documento; no se
  exige ni se simula consulta externa. Datos sólo referidos por paciente/familiar
  permiten alta provisional, sin justificar verified por sí solos.
- `verification` contiene lista de `{field,source_kind,source_reference}`; field
  `full_name`, `birth_date` o `CURP`; referencias descriptivas 1–200, sin adjuntos
  ni copia del número completo del documento. Campo no presente/duplicado → 422.
- El servidor conserva instantánea de los valores contrastados, UUID del verificador
  y fecha UTC propia. Cliente no puede elegir actor, fecha ni marcas de verificación.
  Paciente, evidencia y auditoría se confirman en la misma transacción.

verified es registro de la comprobación declarada por un actor de desarrollo; no
certifica autenticidad documental ni constituye identificación clínica/productiva.
No se añade transición posterior de identidad ni editor general en esta ampliación.

Datos V1 existentes no reciben evidencia fabricada ni se reclasifican en base.
La vista V2 distingue `verification_quality` = `documented`, `pending` o
`legacy_unsubstantiated`. verified de V1 sin evidencia se muestra «Declaración V1;
verificación documentada pendiente», nunca como verificación V2 documentada.
También las nuevas altas por cliente V1 reciben esa calidad al leerlas en V2;
la API antigua no puede producir una evidencia V2 válida por el mero estado verified.

## Episodio

V2 conserva paciente, UUID/folio, tipo y estado open. Añade `intake`:

| Campo | Regla |
|---|---|
| `admitted_at` | Fecha/hora efectiva de ingreso con zona; normalizar UTC y mostrar zona local. No futura según servidor. Diferente de created_at; no rellenar con hora de creación sin confirmación de usuario. |
| `site_id` | UUID de sede activa del catálogo local. |
| `service_id` | UUID de servicio activo asociado a la sede elegida; rechazar pareja incoherente. No significa cama, médico asignado ni autorización clínica. |
| `origin` | Procedencia declarada, texto 1–200. |
| `reason_for_visit` | Motivo referido de atención, texto 1–1000. No diagnóstico, nota firmada ni triage. |

Todos usan state/value. En outpatient/inpatient, admitted_at, site_id y service_id
son obligatorios y conocidos; procedencia/motivo pueden quedar pendientes. En emergency
ningún campo nuevo bloquea la apertura si se desconoce: conservar razón de ausencia
y mostrar «Datos de ingreso pendientes». UUID informado exige catálogo coherente
para cualquier tipo. known implica valor; nunca crear sede/servicio automáticamente
por texto recibido. Si servicio es conocido, sede también debe serlo.

Catálogos propios en PostgreSQL, semillas idempotentes exclusivamente ficticias,
consulta de sedes/servicios activos con admissions.create; sin API de administración,
sin integración externa y sin reglas de asignación hospitalaria aún. FK restrictivas;
pareja sede/servicio y evidencia de verificación protegidas también en base.
Semilla no resucita catálogos suspendidos ni reemplaza valores existentes en silencio.

`admissions.read_intake`, permiso nuevo explícito, protege admitted_at, sede/servicio,
procedencia, motivo y razones de ausencia. Nunca sustituye admissions.read.
Semilla lo asigna a admision-demo/supervisor-demo; consulta-demo conserva proyección
de episodio V1, sin intake. Si el formulario necesita identificar paciente, requiere
además patients.read; el POST conserva admissions.create como autorización de escritura.

Prioridad y triage **diferidos**: no hay selector, código por defecto, puntuación,
recomendación ni regla clínica de atención. Su catálogo/flujo requiere otra definición.
Camas, médico responsable, aseguradoras, cobros, diagnósticos, firma y clínica completa
siguen fuera. El ingreso V2 no cubre todos los mínimos de Admisión §10.

## Evolución de API, persistencia y aceptación

Mantener `/api/v1` y sus respuestas/validaciones para clientes existentes. Endpoints
ampliados bajo `/api/v2` para pacientes, episodios, búsqueda y catálogos. Reutilizar
servicios/reglas comunes; no duplicar reservas de identificadores ni secuencias.
Rutas V2 entregan Location V2; identidad/auditoría V1 siguen reutilizables.
Rutas V2: GET/POST /patients, GET /patients/{id}, POST /admissions,
GET /admissions/{id}, GET /patients/{id}/admissions, GET /catalogs/sites y
GET /catalogs/services?site_id={uuid}. Catálogos paginados con limit/offset/total
V1; services exige sede existente y activa. No publicar datos personales en catálogos.
Idempotencia cubre altas en ambas versiones; la operación incluye versión de contrato
para evitar replay V1/V2 de una misma clave con distintos esquemas/proyecciones.
Huella V2 incluye todo dato ampliado, ausencia y evidencia; excluye search_id y campos
servidor. Replay no reejecuta verificación ni fabrica otra fecha/autor: proyecta
evidencia existente con permisos actuales y conserva su auditoría propia.

No almacenar nuevos datos en logs, URL, respuestas básicas o storage del navegador.
Auditoría de alta ampliada contiene sólo los campos autorizados del contrato; su
acceso continúa restringido a audit.read. Migración no inventa datos para filas V1:
campos nuevos sin evidencia tienen ausencia not_provided/origen legacy identificable.
Persistencia V2-02A: perfiles/descriptores por paciente, contactos/domicilios
subordinados, verificación y evidencia por campo; intake por episodio y catálogos
de sede/servicio. FK restrictivas, cardinalidad de evidencia y coherencia de estados
respaldadas por restricciones/validaciones transaccionales, sin confiar sólo en UI.
El perfil guarda estados/escalares en JSONB validado; las colecciones usan filas
subordinadas con posición 0–9. Evidencia y catálogos tienen tablas propias.
Filas V1 sin ampliación conservan ausencia `not_provided` mediante la proyección;
`administrative_origin`/`intake_origin` señalan `legacy` o `v2`. `is_unidentified`
V1 se entrega null: no se deduce de nombres ausentes. El filtro unidentified V2
consulta sólo la declaración explícita; la búsqueda V1 conserva su contrato.
No volcar todo el perfil en una respuesta de episodio ni copiar motivo al paciente.

Aceptación: migración desde cero y sobre V1 con datos, FK/CHECK y rollback; nuevas
reglas de ausencia/verificación; permiso de intake; catálogos; fechas de ingreso;
regresión V1 e idempotencia/concurrencia de V2. Comandos/casos en
[validación V2](validacion-v2.md). Entrega parcial administrativa, sin afirmar
cumplimiento normativo ni cobertura completa de los módulos.
