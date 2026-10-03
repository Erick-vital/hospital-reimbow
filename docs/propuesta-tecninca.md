# Propuesta técnica de Reimbow HIS

Fecha: 2026-10-02. Actualizado: 2026-10-03. Documento de diseño; no acredita implementación ni aptitud para uso clínico.

## 1. Alcance y evidencia disponible

El objetivo es un sistema hospitalario integrado con identidad única del paciente, expediente longitudinal y espacios de trabajo por área. La coherencia entre módulos, la trazabilidad y las autorizaciones clínicas son parte central del diseño.

Se convirtieron 21 archivos de Word a Markdown en `docs/requerimientos/`, conservando los originales en `requerimientos/drive-download-20261002T204147Z-1-001/`. Se verificó la presencia del texto de los seis documentos con contenido y de la tabla del expediente. Quince originales estaban vacíos; sus Markdown lo indican explícitamente.

| Documento | Requisitos funcionales identificados | No funcionales identificados |
|---|---:|---:|
| [Admisión](requerimientos/1.%20ADMISION.md) | 10 | 7 |
| [Pacientes](requerimientos/2.%20PACIENTE.md) | 15 | 9 |
| [Expediente clínico](requerimientos/3.%20EXPEDIENTE%20CLINICO.md) | 20 | 10 |
| [Médico](requerimientos/4.%20MEDICO.md) | 24 | 10 |
| [Enfermería](requerimientos/5.%20ENFERMERIA.md) | 24 | 12 |
| [Farmacia](requerimientos/6.%20FARMACIA.md) | 26 | 10 |
| Total | 119 | 58 |

Estos conteos cubren los identificadores RF/RNF; los apartados narrativos contienen reglas adicionales que también deberán trazarse. Los catálogos de entidades de origen son preliminares, no un esquema definitivo.

Los documentos vacíos corresponden a Imagen, Banco de sangre, Patología, Epidemiología, Almacén, Compras, Cuentas, Facturación, Intendencia, Mantenimiento, Administración, Dirección, Calidad, Recursos humanos y Reportes e indicadores. No se recibieron documentos numerados 7 y 8. Laboratorio, Estudios, Nutrición, Cirugía, Anestesiología y otros servicios aparecen como dependencias sin especificación completa en esta entrega.

## 2. Decisiones y propuestas

| Tema | Situación actual |
|---|---|
| Base de datos | PostgreSQL desde el inicio, confirmado por el usuario. SQLite descartado. |
| Backend | FastAPI propuesto como base del proyecto, con Pydantic, SQLAlchemy y Alembic. |
| Arquitectura | Monolito modular con reglas de negocio separadas de rutas y persistencia. |
| Frontend | React y TypeScript propuestos para una versión posterior. |
| Autenticación | Cognito recomendado si el despliegue es en AWS; selección definitiva pendiente. |
| Autorización hospitalaria | Permisos, asignaciones y privilegios propios en FastAPI y PostgreSQL. |
| AWS | Destino probable, todavía no confirmado ni desplegado. |
| V1 | Base backend local; excluye Cognito e integraciones externas. |

NestJS fue la primera alternativa considerada para el backend; la propuesta actual utiliza FastAPI. La preferencia por PostgreSQL se basa en validar desde el inicio transacciones, restricciones y operaciones simultáneas sobre camas, inventario y dosis. SQLAlchemy facilita el acceso a distintos motores, pero no iguala sus comportamientos. No se mantendrá una segunda implementación para SQLite.

## 3. Modelo central

- **Paciente:** identidad interna estable, independiente de CURP, correo, nombre y cama; contempla desconocidos, extranjeros y recién nacidos.
- **Expediente:** información clínica longitudinal con una fuente común para alergias, antecedentes y problemas.
- **Episodio:** atención específica vinculada al paciente, con tipo, fechas, servicio y estado.
- **Asignaciones:** equipo responsable, servicio, turno y ubicación con historial.
- **Cuenta:** relación administrativa con el episodio, separada del expediente clínico.

Médico y Enfermería generan y consultan información del mismo expediente. Las vistas longitudinal, por episodio, por problema y cronológica serán distintas formas de consultar esa información. Se combinarán datos estructurados con narrativa clínica.

La conversión de urgencias a hospitalización requiere decidir entre episodio con subepisodios y episodios relacionados. Se conservará continuidad y procedencia en cualquiera de los modelos.

## 4. Responsabilidades de los módulos

| Módulo | Funciones previstas para el sistema completo |
|---|---|
| Pacientes | Identidad, contactos, domicilios, documentos, verificación, homónimos, candidatos a duplicado, fusión y separación controladas. |
| Admisión | Registro rápido, preadmisión, episodios, aseguradoras, camas, reservas, traslados, brazaletes y egreso administrativo. |
| Expediente | Historia, diagnósticos, problemas, alergias, notas, versiones, firmas, adendas, consentimientos, resultados, interconsultas, procedimientos y cronología. |
| Médico | Listas de pacientes, pase de visita, órdenes, prescripción, estudios, interconsultas, alta médica y supervisión. |
| Enfermería | Asignaciones, valoración, signos vitales y su contexto, escalas, planes de cuidados, eMAR, PRN, infusiones, balances, dispositivos, heridas y entrega de turno. |
| Farmacia | Medicamentos y presentaciones, inventario por ubicación y lote, validación, reservas, preparación, dispensación, devoluciones, FEFO, conteos, cadena fría y retiros. |
| Seguridad | Usuarios, roles, permisos, privilegios profesionales, restricciones, supervisión y acceso de emergencia. |
| Servicios compartidos | Auditoría, archivos privados, tareas, notificaciones, impresión, indicadores e integraciones. |

Farmacia y Almacén podrán compartir infraestructura de inventarios, manteniendo sus responsabilidades distintas. Las tareas y recordatorios no sustituirán órdenes clínicas.

## 5. Arquitectura propuesta

- **FastAPI:** API HTTP versionada y documentación OpenAPI.
- **Pydantic:** esquemas de entrada y salida; campos expuestos según el caso de uso.
- **PostgreSQL:** persistencia relacional, restricciones, transacciones y control de concurrencia.
- **SQLAlchemy:** modelos y acceso a datos, con límites explícitos de transacción.
- **Alembic:** migraciones reproducibles desde la primera tabla.
- **React y TypeScript:** frontend futuro con componentes compartidos.
- **Archivos privados:** documentos, fotografías y exportaciones fuera de las tablas principales; proveedor pendiente.
- **Trabajadores y cola persistente:** notificaciones importantes, tareas programadas y reportes futuros.

Las rutas validan solicitudes y delegan en servicios. Los servicios comprueban autorización, reglas, estados y transacciones. La persistencia se encarga de consultas y escrituras. Cada módulo publica servicios explícitos; no modifica silenciosamente información cuyo responsable es otro módulo.

Se iniciará con un monolito modular y una base relacional. No se requieren microservicios para la V1. Las versiones se fijarán después de revisar el entorno y la compatibilidad, sin presentar versiones no comprobadas como decisiones cerradas.

Los cambios sensibles, su auditoría y los eventos pendientes se guardarán de manera coordinada. Cuando haya notificaciones externas, se evaluará un registro transaccional de eventos pendientes con reintentos e idempotencia. Las tareas internas de FastAPI no serán la única garantía de entrega de notificaciones críticas.

## 6. Reglas esenciales para versiones clínicas

### Identidad y continuidad

La búsqueda de posibles duplicados precede a la creación. No habrá fusión automática por similitud. La fusión conservará identificadores y procedencia, resolverá conflictos mediante revisión y permitirá separación autorizada. La separación deberá contemplar registros creados después de la fusión.

Un campo vacío de alergias no significa ausencia de alergias. Los datos desconocidos, no proporcionados, no aplicables y pendientes de verificar se distinguirán cuando corresponda. La ausencia de documentación administrativa no impedirá registrar una urgencia.

### Documentos y supervisión

Una nota tendrá versiones, autor, plantilla, fecha clínica, fecha real de registro y fecha de firma. La firma se vinculará a una versión concreta. Las correcciones posteriores conservarán el original mediante adendas o procedimientos de registro por error.

El MIP elabora una propuesta, la envía y un supervisor autorizado revisa, solicita corrección o aprueba y firma. Autor, modificador, supervisor y firmante conservarán identidades separadas. Una propuesta pendiente no será una orden ejecutable. La autonomía de residentes y estudiantes dependerá de políticas institucionales.

Autenticarse no equivale a firmar una nota. El mecanismo de firma clínica y su revisión normativa siguen pendientes.

### Medicación e inventario

El circuito previsto es: prescripción autorizada → validación farmacéutica cuando corresponda → reserva/preparación → dispensación por lote → verificación → administración o motivo de omisión → expediente.

Prescripción, surtimiento y dosis tendrán estados independientes. Se comprobará nuevamente la vigencia de la orden al ejecutar una acción, aunque la pantalla muestre datos anteriores. Se contemplarán suspensión, devolución, sustitución autorizada, surtimiento parcial, medicamentos propios del paciente y doble verificación individual.

Los saldos se explicarán mediante movimientos por presentación, lote y ubicación. Las correcciones usarán movimientos compensatorios. Caducados, bloqueados, retirados y cuarentenas quedarán excluidos de disponibilidad; las devoluciones se evaluarán antes de reintegrarse. Habrá trazabilidad retrospectiva de lotes hacia pacientes.

### Camas, comunicación y egreso

Se distinguirá ubicación administrativa de temporal. Reservas y asignaciones protegerán contra ocupación concurrente. La liberación podrá conducir a limpieza antes de disponibilidad.

Alta médica y egreso administrativo serán eventos separados. Un resultado crítico registrará notificación y confirmación; reconocerlo no equivale a tratarlo. Las excepciones de urgencia tendrán procedimientos explícitos y auditables.

## 7. Autenticación y autorización futuras

La recomendación es **Cognito para autenticación y autorización clínica propia**. Cognito gestionaría credenciales, recuperación, MFA y federación institucional. FastAPI aplicaría roles y permisos considerando sede, servicio, turno, paciente asignado, privilegio vigente y supervisión.

| Alternativa | Ventaja | Responsabilidad o condición |
|---|---|---|
| Cognito | Servicio administrado, adecuado al posible despliegue AWS. | Dependencia externa, configuración, costes y continuidad por verificar. |
| Keycloak | OIDC/SAML con infraestructura controlada por la organización. | Operar, actualizar, respaldar y mantener disponible el proveedor. Preferible si se requiere identidad local. |
| Autenticación propia | Control de implementación. | Mantener contraseñas, recuperación, MFA y sesiones; no hay necesidad concreta que la justifique actualmente. |

Se propone alta de trabajadores mediante invitación administrativa, sin autorregistro público. La identidad externa se asociaría por emisor/proveedor y `sub` a un usuario interno estable. El correo no será la llave de autoría.

La integración usaría OIDC con código de autorización y PKCE. Para la web se propone una sesión gestionada por FastAPI, cookie `HttpOnly` y `Secure`, y protección CSRF; tokens externos almacenados en el servidor. La selección y prueba de librerías quedan pendientes.

Se validarán firma, emisor, vencimiento, cliente y uso del token cuando se utilicen JWT. La revocación y suspensión deben atenderse explícitamente: comprobar firma y vencimiento no detecta por sí solo un token revocado. Se verificará usuario/sesión activa y se invalidará acceso al deshabilitarlo.

La auditoría clínica permanecerá en el sistema aunque el proveedor tenga sus propios logs. El acceso de emergencia será temporal, con motivo y trazabilidad; no sustituye la autenticación ni elimina la dependencia del proveedor. Debe confirmarse si el hospital requiere nuevos inicios de sesión durante una pérdida de conexión con AWS.

**Nada de esta integración externa se implementa en V1.** La identidad simulada local del plan tampoco será una solución de autenticación para producción.

## 8. Experiencia de uso y evolución

Las interfaces futuras mostrarán identificación permanente, alergias relevantes y cambio evidente de paciente. Los tableros priorizarán pacientes y pendientes de cada rol: admisiones/camas, pase de visita/supervisión, agenda de cuidados/dosis y cola de farmacia/lotes.

Plantillas, escalas y catálogos tendrán versiones. La reutilización de información mostrará origen y fecha para revisión; no convertirá antecedentes o mediciones antiguas en datos actuales.

Se recomienda comenzar por backend y acompañarlo después con un frontend mínimo. La primera demostración operativa será búsqueda → paciente nuevo o existente → episodio → ficha. El primer piloto clínico posterior abarcará ingreso → valoración → nota supervisada → prescripción → dispensación → administración → egreso.

Las fases posteriores incorporarán documentación clínica, medicación, cuidados ampliados, estudios, integraciones y módulos administrativos pendientes. Cada requisito tendrá implementación y criterio de aceptación trazables. La revisión por usuarios de las áreas complementará las pruebas automáticas.

### 8.1 Prioridad del MVP y mejoras reservadas para versiones posteriores

Decisión del usuario del 2026-10-03: estamos construyendo un MVP. **V3 deberá
incluir la simplificación de formularios y priorizar nuevas funcionalidades con
buena base técnica.** La propuesta anterior de dedicar V3 a procedencia,
verificación posterior, regularización de desconocidos, correcciones e historia
de identidad queda aplazada. No se eliminan esos requisitos ni las garantías ya
implementadas; no convertir esta prioridad en autorización de implementar V3.

Simplificación confirmada para el futuro alcance V3: mostrar directamente los
campos de captura, considerar disponible un valor informado y pedir razones de
ausencia sólo cuando correspondan, con opciones pertinentes para cada campo.
Mantener separados valor, ausencia y verificación. No reducir todas las ausencias
a una etiqueta genérica ni inventar información para avanzar. El control repetido
por campo de V2 es una decisión de interfaz, no una presentación obligatoria de
los requerimientos. El diseño concreto y su comprobación funcional se precisarán
en el plan V3; esta actualización no modifica los formularios existentes.

Conservar para próximas versiones las siguientes mejoras. La mayoría ya tienen
fundamento en los originales; aquí se guarda su concreción técnica y el aplazamiento,
sin modificar ni duplicar los documentos fuente:

| Mejora futura | Fundamento original | Concreción propuesta, todavía pendiente |
|---|---|---|
| Procedencia y verificación posterior | [Pacientes §6–7](requerimientos/2.%20PACIENTE.md#6-estados-de-verificación-de-identidad) | Fuentes paciente/familiar/documento y autor/fecha; verificar campos después del alta, conservando la evidencia de cada comprobación. |
| Completar identidad de un desconocido | [Pacientes §13](requerimientos/2.%20PACIENTE.md#13-paciente-desconocido) | Conservar UUID/folio/episodios al completar identidad; conflictos de identificadores se envían a revisión. Fusión/separación requieren diseño y aceptación propios. |
| Correcciones con historial y permisos | [Admisión §26](requerimientos/1.%20ADMISION.md#26-corrección-de-datos) y [Pacientes §37](requerimientos/2.%20PACIENTE.md#37-auditoría) | Motivo, antes/después, autor/fecha y autorización adicional para cambios críticos; protección contra sobrescritura concurrente y reevaluación de la evidencia afectada. |
| Historia comprensible de identidad | [Pacientes §7/37](requerimientos/2.%20PACIENTE.md#37-auditoría) | Vista de procedencia, verificaciones y cambios con permisos. La pantalla concreta es propuesta de diseño; los originales exigen los registros/auditoría, no esta interfaz específica. |

### 8.2 Recomendación de ampliación funcional para V3 — por decidir

Después de cerrar V2-06, se recomienda un **expediente clínico básico** que permita
el recorrido paciente → episodio → signos vitales/alergias → nota médica en borrador
→ consulta compartida autorizada. Esta recomendación responde a la prioridad de
ampliar el MVP; se concreta en el [plan V3 preparado](../plans/v3-expediente-basico.md),
solicitado el 2026-10-03. Su preparación no autoriza implementación; contrato, roles
y revisión de formularios siguen pendientes.

| Bloque sugerido | Funcionalidad visible | Fundamento y límite inicial |
|---|---|---|
| Formularios simples | Captura directa y ausencias pertinentes. | Prioridad confirmada en §8.1; conservar reglas de integridad V2. |
| Lista de episodios abiertos | Encontrar atenciones por tipo/sede/servicio disponibles y abrir su contexto clínico. | [Médico §27–29](requerimientos/4.%20MEDICO.md#27-panel-principal-del-médico); recorte del tablero, sin aparentar camas/asignaciones todavía no implementadas. |
| Expediente básico | Vista por paciente y episodio, identificación permanente y resumen de la información realmente registrada. | [Expediente §4–7 y EHR-RF-001/002](requerimientos/3.%20EXPEDIENTE%20CLINICO.md#4-expediente-longitudinal); sin afirmar expediente completo. |
| Registro y consulta de signos vitales | Mediciones con unidades, fecha clínica/registro, autor y contexto pertinente; tabla y evolución básica. | [Enfermería §10–11](requerimientos/5.%20ENFERMERIA.md#10-signos-vitales) y [Expediente §23](requerimientos/3.%20EXPEDIENTE%20CLINICO.md#23-signos-vitales); sin reglas de alerta, triage ni recomendaciones clínicas improvisadas. |
| Alergias básicas | Registro compartido, fuente y autor; distinguir no documentado, desconocido y sin alergias conocidas. | [Expediente §12 / EHR-RF-010](requerimientos/3.%20EXPEDIENTE%20CLINICO.md#12-alergias-y-reacciones-adversas); no deducir ausencia desde una lista vacía. |
| Nota médica inicial | Una plantilla acotada con motivo, antecedentes relevantes, exploración, valoración y plan narrativo; guardar/recuperar borrador con versiones y autoría. | [Expediente §13–15 / EHR-RF-003/004/019](requerimientos/3.%20EXPEDIENTE%20CLINICO.md#13-notas-clínicas); explícitamente no firmada, sin órdenes ejecutables ni firma clínica simulada como válida. |

La misma medición o alergia tendrá una fuente clínica común, consultable por Médico
y Enfermería según permisos, sin copias divergentes entre módulos. Como referencia
de modelado, [FHIR R5 Observation](https://hl7.org/fhir/R5/observation.html) separa
mediciones de diagnósticos y relaciona observaciones con paciente, encuentro y tiempo
clínico. Consultar ese modelo no implica implementar interoperabilidad FHIR en V3.

Base técnica mínima propuesta: PostgreSQL/migraciones, vínculo inequívoco a paciente
y episodio, permisos del servidor por operación, autor/fechas, auditoría transaccional,
protección de ediciones concurrentes y pruebas de navegador/API. No convertir estas
bases en el desarrollo completo de las mejoras administrativas aplazadas en §8.1.
El MVP local mantiene datos ficticios e identidad demo explícita; acceso de personas
reales exige abordar autenticación antes de habilitarlo.

Aceptación propuesta: crear paciente/episodio, capturar mediciones como Enfermería,
consultarlas como Médico junto con alergias, guardar una nota en borrador y volver
a abrirla sin perder datos ni confundir paciente/episodio. Roles clínicos demo y su
matriz deberán definirse expresamente; los actores administrativos V2 no los sustituyen.
Firma/supervisión clínica completa, prescripción/dispensación/administración,
camas/traslados, cobros, adjuntos e integraciones se evaluarán en siguientes versiones.

## 9. Integraciones, operación y decisiones abiertas

Se evaluarán adaptadores HL7/FHIR y DICOM/PACS según los sistemas destinatarios, versiones, licencias y contratos. No se afirma compatibilidad por reservar una interfaz. Compras, Cuentas, Facturación y demás áreas requieren completar sus especificaciones antes de comprometer alcance.

Pendientes: episodios/subepisodios; mecanismo de firma; conservación y revisión normativa; catálogos y fuentes farmacológicas; unidades y conversiones; supervisión; urgencias; cobro al dispensar o administrar; equipos e impresoras; usuarios simultáneos, sedes y volumen; infraestructura y disponibilidad del proveedor de identidad.

La operación futura incluirá protección de conexiones y archivos, auditoría, copias de base y documentos, restauración ensayada y contingencia con reconciliación posterior. Los objetivos de pérdida admisible de datos y tiempo de recuperación deben acordarse. Las reglas de soporte clínico, escalas e interacciones requieren validación antes de uso real.

## 10. Fuentes técnicas consultadas

- [FastAPI](https://fastapi.tiangolo.com/) y [tareas en segundo plano](https://fastapi.tiangolo.com/tutorial/background-tasks/).
- [SQLAlchemy: transacciones](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html).
- [PostgreSQL: bloqueos](https://www.postgresql.org/docs/current/explicit-locking.html) y [respaldo y recuperación](https://www.postgresql.org/docs/current/backup.html).
- [SQLite: usos y concurrencia](https://www.sqlite.org/whentouse.html) y [diferencias de comportamiento](https://www.sqlite.org/quirks.html), consultados para la alternativa descartada.
- [React](https://react.dev/learn) y [NestJS: módulos](https://docs.nestjs.com/modules), alternativa backend inicial.
- [Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools.html), [autorización y PKCE](https://docs.aws.amazon.com/cognito/latest/developerguide/authorization-endpoint.html), [verificación de JWT](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html) y [precios](https://aws.amazon.com/cognito/pricing/).
- [Keycloak](https://www.keycloak.org/securing-apps/overview) y [FHIR](https://hl7.org/fhir/overview.html).

La propuesta se concreta para V1 en [el plan de implementación](../plans/v1-base-backend.md). Los documentos de requerimientos conservan la intención funcional original.
