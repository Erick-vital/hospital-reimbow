# V3 — Formularios simples y expediente clínico básico

Fecha: 2026-10-03. Estado: **V3-03 cerrada técnicamente; revisión funcional final pendiente**.
El usuario autorizó comenzar la primera etapa y después solicitó cerrarla,
aplazando la inspección visual hasta disponer de funcionalidad al final de V3.
La simplificación y el crecimiento funcional del MVP son prioridades confirmadas.
V2-01–06 tienen cierre técnico y commit `cc86c8e`; sus revisiones humanas pendientes
se conservan. D01–D06 quedan como base de diseño revisable en la entrega funcional;
no se registra una inspección realizada ni aprobación individual de esas decisiones.
V3-02 y V3-03 implementadas por autorización posterior explícita; V3-04–07 sin iniciar.

## Objetivo y recorrido

Ampliar el MVP local para encontrar una atención abierta, consultar el contexto
del paciente, registrar signos vitales y alergias y guardar una nota médica en
borrador. Médico y Enfermería consultarán la misma información según permisos.
Antes, simplificar la captura administrativa que hoy repite selectores por campo.

Recorrido de aceptación: captura directa de paciente → apertura de episodio →
lista de atenciones → contexto clínico → mediciones y alergias → nota en borrador
→ consulta posterior por otro actor autorizado. Siempre distinguir PAC de EPI.

Dependencias: cierre técnico de [V2](v2-interfaz-admision.md), conservación de su
evidencia y registro separado de sus revisiones humanas pendientes. Una observación
funcional de V2 deberá resolverse o anotarse como limitación antes de trasladar su
flujo a V3; no convertir las pruebas automáticas en aprobación del usuario.

## Decisiones y límites

- Prioridad confirmada: formularios simples y más funciones útiles del MVP con
  una base técnica sólida; no dedicar esta versión a perfeccionar la identidad.
- PostgreSQL, FastAPI/Pydantic/SQLAlchemy/Alembic y React/TypeScript existentes;
  monolito modular, con reglas y permisos del servidor separados de las rutas.
- Datos ficticios, ejecución local e identidad demo explícita exclusivamente en
  desarrollo/test. Definir nuevos actores clínicos; los administrativos no reciben
  acceso clínico por herencia. Sin autenticación real, AWS ni uso clínico real.
- Identidad UUID y folios del servidor, permisos sobre lectura y escritura,
  auditoría transaccional y fechas/autoría reales del servidor en cada operación.
- Expediente longitudinal y episodio son conceptos distintos. Alergias pertenecen
  al paciente; mediciones y notas se vinculan además a la atención concreta.
- No duplicar tablas clínicas entre Médico y Enfermería ni tomar una medición
  antigua como actual. La interfaz indica fecha clínica y fecha de captura.
- Nota exclusivamente en borrador: sin firma, aprobación clínica, órdenes
  ejecutables ni publicación que aparente validez clínica.

Quedan para futuras versiones la procedencia administrativa ampliada, verificación
posterior, completar la identidad de desconocidos, fusión/separación, correcciones
críticas y la historia visual de identidad. Sus fundamentos y propuestas están en
[propuesta §8.1](../docs/propuesta-tecninca.md#81-prioridad-del-mvp-y-mejoras-reservadas-para-versiones-posteriores).
Conservar las garantías V2 ya implementadas. También se difieren firma/supervisión
clínica completa, diagnósticos estructurados, prescripciones, farmacia, eMAR,
triage/alertas clínicas, camas/traslados, egreso, cobros, documentos e integraciones.

## Etapas y aceptación

### V3-01 — Diseño y contrato acotados

Estado: **cerrada el 2026-10-03 por instrucción explícita del usuario**.
[Contrato revisión 1](../docs/contrato-v3.md), [boceto navegable](../docs/bocetos-v3.html),
[matriz](../docs/validacion-v3.md), [evidencia/guion](../docs/evidencia-v3-01.md).

- [x] Revisar los apartados pertinentes de requerimientos y elaborar contrato de
  entradas/salidas, permisos, ausencias, fechas, versiones y errores.
- [x] Preparar bocetos de formularios directos, tablero, cabecera clínica,
  signos vitales, alergias y nota; comprobación local desktop/móvil documentada.
- [x] Registrar aplazamiento de la inspección visual de formularios a la entrega
  funcional final, solicitado por el usuario; no se realizó M3-01.
- [x] Definir propuesta de actores medico-demo/enfermeria-demo y permisos por
  operación, acceso de consulta y aislamiento de actores administrativos.
- [x] Conservar D02/D03 como base de diseño tras el cierre solicitado: acceso demo
  global y lectura compartida de borradores; no usar «mis pacientes» sin asignaciones.
- [x] Conservar plantilla, mediciones/unidades/contextos y mínimo de alergias
  D04–D06 como base revisable al final. Sin umbrales/alertas inventados.
- [x] Registrar matriz de aceptación, cobertura parcial y límites.
- [x] Registrar respuesta explícita: cerrar V3-01 y aplazar inspección visual;
  conservar aprobación funcional para el recorrido final M3-02.

Aceptación: contrato y diseño revisables, cada campo y acción con regla definida;
ausencias diferenciadas y roles sin privilegios implícitos. La instrucción reciente
del usuario sustituye la revisión visual previa por revisión de la funcionalidad
al final; D01–D06 quedan como base, sin bloquear dependientes por M3-01.
Conservar los criterios técnicos de todas las etapas y la aceptación final M3-02.

### V3-02 — Simplificar formularios administrativos (prioridad obligatoria)

Estado: **cierre técnico el 2026-10-03**.
[Evidencia y comandos](../docs/evidencia-v3-02.md): TypeScript/build correctos,
51 pruebas navegador/API y 316 backend PostgreSQL pasan. Revisión manual de
formulario y prueba completada por el usuario; sin cambios de API, permisos,
migraciones o configuración.

- [x] Mostrar directamente nombre, nacimiento y demás campos habituales;
  inferir `known` cuando haya un valor válido, sin selector previo repetido.
- [x] Ofrecer razones de ausencia cuando falte un dato, con opciones pertinentes
  por campo. No confundir desconocido, no proporcionado y no aplicable.
- [x] Separar disponibilidad de verificación; conservar búsqueda previa,
  evidencia cuando corresponda, permisos y descriptores del desconocido.
- [x] Aplicar el patrón a paciente/ingreso y listas de contactos; mantener
  confirmación explícita, accesibilidad y reintentos con cuerpo/clave congelados.
- [x] Verificar navegador/API y regresión: no inventar valores, no perder
  ausencias al revisar y no invalidar el contrato administrativo existente.
- [x] Revisión manual del formulario administrativo y la prueba realizada por
  el usuario el 2026-10-03; confirma que puede tacharse esta parte del plan.

Aceptación: registrar paciente y urgencia sin escoger «conocido» para cada valor;
un dato ausente conserva su significado y una identidad disponible sigue pudiendo
ser provisional. Aplicar D01 como base de diseño; revisión manual de esta parte
completada posteriormente por el usuario. El resto de M3-02 sigue pendiente.

### V3-03 — Lista de atenciones y contexto clínico

Estado: **cierre técnico el 2026-10-03**, autorización «implementa V3-03».
[Evidencia y comandos](../docs/evidencia-v3-03.md), [guía](../docs/desarrollo-v3.md):
339 backend PostgreSQL y 57 navegador/API pasan; TypeScript/build correctos.
Migración 0007 y actores clínicos preparados en hospital_dev/hospital_test.
Sólo tres permisos clínicos implementados; administrativos con listas explícitas.
Semilla conserva UUID, suspensiones y permisos/asignaciones revocados.
Signos/alergias/notas sin secciones simuladas; C04 de esos módulos se comprobará
al implementarlos en V3-04–06. Revisión funcional final M3-02 pendiente.

- [x] Lista paginada de episodios abiertos, con filtros por tipo/sede/servicio
  que estén disponibles; paciente identificado por nombre autorizado y PAC/EPI.
- [x] API y permisos clínicos explícitos; sin listado de demografía/intake
  restringidos ni ampliación de los permisos de consulta-demo.
- [x] Vista clínica por episodio y acceso longitudinal del paciente, con cabecera
  permanente, cambio de contexto evidente y estados vacíos honestos.
- [x] Mostrar sólo secciones implementadas y separar información de otras
  atenciones; limpiar contexto, borradores y resultados al cambiar paciente/actor.

Aceptación: localizar dos episodios, abrirlos y regresar sin mezclar información;
acceso directo y API también comprueban permisos. No mostrar camas/equipos ficticios.

### V3-04 — Registro y consulta de signos vitales

- [ ] Migraciones/modelos y contrato para mediciones acordadas en V3-01,
  unidades explícitas, fecha clínica con zona, autor y fecha de registro.
- [ ] Captura vinculada a paciente/episodio, contexto pertinente y validación
  numérica/unidades; dato no medido no equivale a cero.
- [ ] Registro idempotente y auditoría en la misma transacción; historial
  consultable por roles autorizados, sin sobrescrituras silenciosas.
- [ ] Tabla y evolución básica por medición, conservando unidades y contexto;
  las mediciones previas muestran su fecha y no se presentan como actuales.

Aceptación: Enfermería captura valores ficticios y Médico consulta el mismo registro;
reintento no duplica, fechas/unidades se conservan y actores sin permiso son rechazados.
Correcciones o registros por error deberán tener procedimiento explícito antes de
habilitarlos; no agregar un borrado ordinario como atajo.

### V3-05 — Alergias compartidas

- [ ] Modelo longitudinal del paciente con estado explícito: no documentado,
  desconocido, sin alergias conocidas o alergias registradas.
- [ ] Agente/sustancia, reacción y fuente según contrato, autor y fechas;
  distinguir alergia de otra reacción adversa si ambos conceptos se admiten.
- [ ] Mostrar resumen visible en contexto clínico y detalle compartido entre
  episodios; registrar revisiones con historial y concurrencia controlada.
- [ ] No inferir «sin alergias» desde una lista vacía ni eliminar historia al
  cambiar una declaración. Permisos, idempotencia y auditoría de cada cambio.

Aceptación: misma información al abrir dos episodios del paciente, estados sin
ambigüedad y conflicto explícito si dos actores modifican la misma versión.
Sin reglas de interacciones farmacológicas ni recomendaciones terapéuticas.

### V3-06 — Nota médica inicial en borrador

- [ ] Una plantilla acotada: motivo, antecedentes relevantes, exploración,
  valoración y plan narrativo; versión de plantilla y límites de texto definidos.
- [ ] Guardar/recuperar borrador en PostgreSQL con paciente/episodio, autor,
  fecha clínica y de registro, versiones conservadas y permisos de autoría.
- [ ] Edición explícita con versión esperada; un conflicto no sobrescribe el
  trabajo de otro usuario. Creación/reintento idempotentes y auditoría transaccional.
- [ ] Rotular «Borrador no firmado» en lista/detalle y registrar autor/modificador
  separados. Consulta por otro rol sólo según permisos acordados.
- [ ] No generar órdenes, diagnósticos activos ni copiar valores antiguos
  automáticamente a la nota. Cambiar paciente no arrastra contenido del anterior.

Aceptación: guardar, reabrir, editar y consultar versiones; dos ediciones simultáneas
producen un conflicto recuperable. El texto del plan no activa acciones clínicas.

### V3-07 — Recorrido, recuperación y entrega

- [ ] Pruebas PostgreSQL/API/navegador del recorrido completo y regresión V1/V2.
- [ ] Permisos por rol/operación, campos restringidos, pérdida de respuesta,
  concurrencia real, cambio de contexto y errores con correlación segura.
- [ ] Migración desde V2 conservando datos y migración en base nueva aislada;
  preparación repetible, guía, verificadores y evidencia reproducible.
- [ ] Comprobar teclado, etiquetas, foco, cabecera, móvil y tiempos observados
  sin extrapolar a un SLA ni presentar revisión técnica como aceptación clínica.
- [ ] Preparar M3-02, registrar respuesta explícita y actualizar plan/ESTADO.

Aceptación técnica: recorrido reproducible, persistencia sin duplicados o mezcla de
contextos y ediciones concurrentes protegidas. Aceptación funcional: M3-02 aprobada
expresamente; mientras falte, declarar revisión pendiente.

## Requerimientos y recorte

| Fuente original | Entrega V3 | Límite |
|---|---|---|
| Pacientes §5–10/13 y Admisión §8–11 | V3-02, presentación simple de captura/ausencias | No ampliar administración de identidad. |
| Médico §27–29 | V3-03, lista y contexto de atenciones | Acceso demo global como base; sin tablero completo, asignaciones ni turnos. |
| Expediente §4–7, EHR-RF-001/002 | V3-03, consulta longitudinal/por episodio de datos implementados | No expediente completo ni vista por problema. |
| Enfermería §10–11 y Expediente §23 | V3-04, mediciones/contexto/historial | No escalas, alertas, triage ni tareas de turno. |
| Expediente §12, EHR-RF-010 | V3-05, alergias compartidas y estados explícitos | No motor de interacciones ni conciliación farmacológica. |
| Expediente §13–15, EHR-RF-003/004/019 | V3-06, borrador/versiones/autoría | Cobertura parcial: firma/adendas/supervisión diferidas. |
| Permisos/auditoría/concurrencia originales | Todas las etapas | Identidad local ficticia, sin conformidad normativa afirmada. |

Fuentes: [Pacientes](../docs/requerimientos/2.%20PACIENTE.md),
[Admisión](../docs/requerimientos/1.%20ADMISION.md),
[Expediente](../docs/requerimientos/3.%20EXPEDIENTE%20CLINICO.md),
[Médico](../docs/requerimientos/4.%20MEDICO.md),
[Enfermería](../docs/requerimientos/5.%20ENFERMERIA.md).
No modificar documentos originales para hacerlos coincidir con el MVP.

## Revisiones y siguiente paso

M3-01: [respuesta y entregables](../docs/evidencia-v3-01.md); inspección del boceto
aplazada por el usuario. V3-01 cerrada; D01–D06 son la base de diseño revisable.
M3-02: recorrido ficticio paciente → episodio → mediciones/alergias → borrador →
consulta compartida, con errores/reintentos y permisos. Incorporar la inspección
visual de formularios y vistas implementadas; aprobación funcional final pendiente.

V2-06 y su commit ya están cerrados técnicamente. V3-01 cerrada por instrucción:
21 comprobaciones locales del boceto pasaron, sin errores de script; capturas
desktop/móvil inspeccionadas técnicamente. No prueban API/PostgreSQL ni aceptación
humana. Riesgo de semilla global identificado en V3-01 y resuelto en V3-03:
Admisión/Supervisor conservan listas administrativas explícitas.
V3-02 cerrada técnicamente tras autorización explícita de implementación;
[evidencia](../docs/evidencia-v3-02.md) y matriz A01–A07 comprobadas.
V3-03 cerrada técnicamente: lista/contexto/longitudinal, permisos y auditoría
comprobados en [evidencia](../docs/evidencia-v3-03.md).
Siguiente etapa: V3-04, signos vitales; V3-04–07 sin iniciar y sin autorización
de implementación por esta entrega. Cierre técnico no equivale a aceptación funcional.
M3-01 no bloquea las etapas siguientes; revisiones V2 conservan estado separado.
