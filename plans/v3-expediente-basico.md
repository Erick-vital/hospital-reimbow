# V3 — Formularios simples y expediente clínico básico

Fecha: 2026-10-03. Estado: **plan preparado; implementación no iniciada**.
Preparación solicitada por el usuario. La simplificación y el crecimiento funcional
del MVP son prioridades confirmadas; el recorte clínico concreta la recomendación
conversada. Crear este plan no autoriza iniciar V3. V2-06 sigue siendo la tarea activa.

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

- [ ] Revisar los apartados pertinentes de requerimientos y elaborar contrato de
  entradas/salidas, permisos, ausencias, fechas, versiones y errores.
- [ ] Preparar bocetos de formularios directos, tablero, cabecera clínica,
  signos vitales, alergias y nota; revisar primero los formularios con el usuario.
- [ ] Definir actores médico-demo/enfermeria-demo, permisos por operación y
  acceso de consulta. Precisar si se usa acceso demo global o asignaciones mínimas;
  no etiquetar como «mis pacientes» un listado sin asignaciones implementadas.
- [ ] Acordar plantilla de nota, mediciones/unidades/contextos admitidos y
  contenido mínimo de alergias. No inventar umbrales diagnósticos o alertas.
- [ ] Registrar matriz de aceptación, límites y respuesta funcional M3-01.

Aceptación: contrato y diseño revisables, cada campo y acción con regla definida;
ausencias diferenciadas y roles sin privilegios implícitos. Resolver estas decisiones
antes de construir sus flujos dependientes; avanzar trabajo independiente autorizado.

### V3-02 — Simplificar formularios administrativos (prioridad obligatoria)

- [ ] Mostrar directamente nombre, nacimiento y demás campos habituales;
  inferir `known` cuando haya un valor válido, sin selector previo repetido.
- [ ] Ofrecer razones de ausencia cuando falte un dato, con opciones pertinentes
  por campo. No confundir desconocido, no proporcionado y no aplicable.
- [ ] Separar disponibilidad de verificación; conservar búsqueda previa,
  evidencia cuando corresponda, permisos y descriptores del desconocido.
- [ ] Aplicar el patrón a paciente/ingreso y listas de contactos; mantener
  confirmación explícita, accesibilidad y reintentos con cuerpo/clave congelados.
- [ ] Verificar navegador/API y regresión: no inventar valores, no perder
  ausencias al revisar y no invalidar el contrato administrativo existente.

Aceptación: registrar paciente y urgencia sin escoger «conocido» para cada valor;
un dato ausente conserva su significado y una identidad disponible sigue pudiendo
ser provisional. M3-01 precede a implementar el diseño concreto de estos formularios.

### V3-03 — Lista de atenciones y contexto clínico

- [ ] Lista paginada de episodios abiertos, con filtros por tipo/sede/servicio
  que estén disponibles; paciente identificado por nombre autorizado y PAC/EPI.
- [ ] API y permisos clínicos explícitos; sin listado de demografía/intake
  restringidos ni ampliación de los permisos de consulta-demo.
- [ ] Vista clínica por episodio y acceso longitudinal del paciente, con cabecera
  permanente, cambio de contexto evidente y estados vacíos honestos.
- [ ] Mostrar sólo secciones implementadas y separar información de otras
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
| Médico §27–29 | V3-03, lista y contexto de atenciones | No tablero completo, asignaciones/turnos pendientes de decisión. |
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

M3-01: contrato/bocetos y especialmente formularios; revisión antes de implementarlos.
M3-02: recorrido ficticio paciente → episodio → mediciones/alergias → borrador →
consulta compartida, con errores/reintentos y permisos. Ambas pendientes.

Primero cerrar V2-06 y su commit solicitado. Cuando se autorice implementar V3,
iniciar V3-01 y registrar decisiones pendientes, sin asumir aprobado un diseño clínico
por la sola creación de este documento. No hay etapas V3 implementadas ni probadas.
