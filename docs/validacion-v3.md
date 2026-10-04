# Matriz de aceptación V3 — revisión 1

Fecha: 2026-10-03. **V3-01 cerrada por instrucción del usuario; inspección aplazada.**
V3-02/A01–A07 comprobados técnicamente en [evidencia V3-02](evidencia-v3-02.md).
C01–C04/V3-03 comprobados en [evidencia V3-03](evidencia-v3-03.md), salvo lecturas
de signos/alergias/notas aún no implementadas. Casos V3-04–07 preparados, no ejecutados. Contrato propuesto en [contrato V3](contrato-v3.md).
Comprobaciones de esta entrega y guion humano en [evidencia V3-01](evidencia-v3-01.md).

## Revisión de V3-01

R01 y R06 comprobados técnicamente en la evidencia. Diseño de R02–R05 documentado;
su inspección humana se traslada a M3-02, sin marcarla realizada. R07 resuelto con
la instrucción explícita de cierre/aplazamiento, sin aprobación funcional final.

| ID | Comprobación | Resultado exigido / evidencia |
|---|---|---|
| R01 | Contrastar requerimientos y código V2 vigente. | Campos/reglas/recortes trazados; no alterar originales. Contrato §§2–11 y tabla siguiente. |
| R02 | Revisar captura directa con ausencia, lista vacía y desconocido. | Campo visible sin escoger known; razones pertinentes; confirmación conserva significado; D01, inspección final M3-02. |
| R03 | Revisar permisos/cabecera/listado. | D02/D03: acceso global demo explícito, administrativos sin clínica, campos limitados y PAC distinto de EPI. |
| R04 | Revisar mediciones y alergias. | D04/D05: unidades/contextos/fechas y estados explícitos, ausencia distinta de cero y de sin alergias. |
| R05 | Revisar plantilla/autores/versiones/errores. | D06: borrador parcial/no firmado, sólo autor edita, conflicto conserva trabajo; sin órdenes. |
| R06 | Abrir boceto desktop/móvil y recorrerlo. | Sin error de script; etiquetas/foco/cabecera legibles. Es comprobación del boceto, no API/permisos/transacciones. |
| R07 | Registrar respuesta a la revisión M3-01. | Respuesta literal del 2026-10-03 en evidencia: cerrar etapa y aplazar inspección visual. M3-02 mantiene aceptación final pendiente. |

## Concordancia y límites

| Fuente pertinente | Propuesta V3 | Cobertura y exclusión explícita |
|---|---|---|
| Pacientes §5–10/13; Admisión §8–11 | Captura directa con reglas V2, evidencia/ausencias separadas. | Presentación simplificada de campos implementados. País/entidad de nacimiento, correo, fotografía, representación/pago, completar desconocidos y correcciones de identidad diferidos. |
| Médico §27–29 | Atenciones abiertas por tipo/sede/servicio, PAC/EPI. | Sin «mi turno/mis pacientes», camas, diagnósticos, pendientes u órdenes. D02 decide acceso demo global, no asignaciones. |
| Expediente §4–7; EHR-RF-001/002 | Vista longitudinal y por episodio de signos, alergias y borradores. | No expediente/resumen completo, vista por problema, diagnósticos ni resultados. Cabecera con sólo campos autorizados. |
| Enfermería §10–11; Expediente §23 | TA, FC, FR, temperatura, SpO₂, peso/talla, contexto/tabla/gráfica. | Dolor, glucosa, IMC calculado, escalas y alertas diferidos; rangos de representación no son umbrales clínicos. |
| Expediente §12; EHR-RF-010 | Estado/revisiones de alergias referidas, sustancia/reacción/fuente/observación. | Cobertura parcial: severidad, fecha aproximada del evento y verificación clínica diferidas; no confundir intolerancia/reacción adversa/contraindicación con alergia. |
| Expediente §13–15; EHR-RF-003/004/008/019 | Una plantilla inicial en borrador, versiones y autoría. | RF-003 cubierto parcialmente: sólo una plantilla. Firma, adendas, otras notas y supervisión diferidas. |
| EHR-RF-020 y reglas comunes | Auditoría de acceso/escritura, permisos, contexto y transacciones. | Sólo propuesta en V3-01; controles por comprobar posteriormente. Sin autenticación real ni conformidad normativa afirmada. |

Fuentes conservadas en [requerimientos](requerimientos/) y
[propuesta técnica](propuesta-tecninca.md). No reinterpretar un requisito completo
como aprobado por este recorte; la revisión funcional se hará sobre la entrega
implementada en M3-02, según la instrucción de cierre de V3-01.

## Casos preparados para implementación

**A01–A07 y C01–C04 comprobados** (alcance implementado); V3-04–07 pendientes hasta su etapa. Integración sobre PostgreSQL; no SQLite ni
respuestas simuladas para evidenciar persistencia, permisos o concurrencia.

| ID / etapa | Caso reproducible | Aceptación |
|---|---|---|
| A01 / V3-02 | Escribir nombre/nacimiento/sexo/teléfono; revisar cuerpo enviado. | Ningún known previo, cuerpo V2 válido, provisional no se vuelve verified. |
| A02 / V3-02 | Elegir razón, escribir valor, borrarlo, revisar y volver. | Razón elegida restaurada, nunca conocida con null; espacios no producen valor vacío válido. |
| A03 / V3-02 | Desconocido con descriptores opcionales, o sin ellos; búsqueda vigente. | No identidad ficticia, rango no es nacimiento; urgencias abre con datos pendientes. |
| A04 / V3-02 | Lista sin declarar / ninguna explícita / una fila / quitar última. | not_provided/unknown distinto de known/[]; contactos/domicilios incompletos bloquean hasta completar/quitar. |
| A05 / V3-02 | Consulta/hospitalización sin ingreso/sede/servicio; cambiar sede. | Requeridos, coherencia por API; urgencias admite ausencias. Servicio anterior se descarta con aviso. |
| A06 / V3-02 | Supervisor verifica; cambiar valor/fuente; Admisión intenta verified. | Evidencia/búsqueda invalidada como V2; servidor rechaza privilegio ausente. |
| A07 / V3-02 | Respuesta perdida después de commit, 409/422, doble clic, recarga. | Mismo cuerpo/clave, sin duplicado; borrador preservado cuando procede; aviso/reconciliación después de perder memoria. |
| C01 / V3-03 | Sembrar repetidamente roles antiguos/nuevos y suspensiones existentes. | Administrativos conservan listas explícitas V2; consulta-demo no gana campos ni clínica; no reactivar actores. |
| C02 / V3-03 | Dos episodios de Alfa, uno de Beta; filtros/totales/URL directa. | Lista paginada sólo open, sede/servicio reales del catálogo; sin cama/turno ficticios. |
| C03 / V3-03 | Abrir A/B/Beta, atrás/recarga; respuestas retrasadas del contexto anterior. | PAC/EPI correctos, resultados/borradores/intenciones limpios, ninguna respuesta antigua repuebla. |
| C04 / V3-03 | Actores antiguos y actor clínico con permiso de lectura de sección revocado. | 401/403 según identidad; contexto omite sección sin permiso y no revela demografía/intake ampliados. |
| S01 / V3-04 | Enfermería mide y Médico lee registro con unidades/contextos y dos fechas. | Mismo UUID/valores; lectura real desde PostgreSQL por ambos, sin copias por rol. |
| S02 / V3-04 | Vacío, cero explícito, presión parcial, unidad extraña, NaN/cadena, fecha sin zona/futura/anterior a ingreso conocido. | Ausencia null, 0 conservado, inválidos 422 sin valores en error. Contexto O₂ coherente. |
| S03 / V3-04 | Misma intención simultánea: barrera y conexiones independientes; HTTP simultáneo. | Un registro y éxito de creación; replay propio, mismo plazo/fechas; fallo de auditoría revierte todo. |
| S04 / V3-04 | Gráfica/historial con otra atención y huecos. | Sólo episodio/unidad seleccionados, fechas/contextos visibles; no datos antiguos «actuales», sin ceros/interpolación inventados. |
| L01 / V3-05 | Paciente sin revisión → unknown → recorded → no_known_allergies. | Cuatro estados distintos; revisión explícita con fuente/fecha/autor/motivo; historial conservado. |
| L02 / V3-05 | Abrir dos episodios del mismo paciente tras revisión. | Mismo estado/versión longitudinal; retirada confirmada conserva sustancia en versión anterior. |
| L03 / V3-05 | Dos intenciones con expected_version 0 o N, barrera/conexiones independientes. | Sólo una nueva revisión, otra 409; cabecera inicial única. Borrador del perdedor conservado. |
| L04 / V3-05 | Replay de PUT ya confirmado después de otra revisión; revocar permiso. | Devuelve versión original antes de vencer; no reevalúa expected_version; 403 si permiso revocado. |
| N01 / V3-06 | Nota parcial → reabrir → editar propia → versiones. | Al menos una sección, plantilla 1, draft permanente; originales/fechas y texto preservados. |
| N02 / V3-06 | Enfermería lee; intenta editar; otro UUID médico intenta editar; campos servidor extra. | Lectura según D03, escritura 403; campo extra 422. Autor/modificador separados, sin privilegio por etiqueta. |
| N03 / V3-06 | Dos pestañas y conexiones del mismo autor con versión igual. | Una edición, otra 409 VERSION_CONFLICT; comparación manual recuperable; no sobrescritura silenciosa. |
| N04 / V3-06 | Replay confirmado, pérdida de respuesta, vencimiento, rollback de auditoría. | Versión original, sin incremento duplicado; congelación/reconciliación y rollback transaccional. |
| T01 / V3-07 | Migrar base aislada nueva y otra con datos V2; upgrade repetido/check; preparar dos veces. | Datos/folios/permisos/suspensiones/secuencias conservados; FK/CHECK/UNIQUE y PostgreSQL comprobados. |
| T02 / V3-07 | Recorrido completo y regresión V1/V2 + estados red/base/autorización. | Evidencia reproducible, sin datos clínicos en storage/logs/URL ni permisos implícitos; sin mezcla de pacientes. |
| T03 / V3-07 | Teclado/foco/errores/lectura móvil y tiempos locales. | Etiquetas/unidades/contexto legibles y acciones alcanzables; observaciones sin afirmar SLA o aceptación humana. |
| T04 / V3-07 | M3-02 con actores/datos ficticios, inspección visual de formularios/vistas y respuesta explícita. | Revisar también D01–D06, registrar aceptación o correcciones; no cerrar validación funcional por pruebas automáticas. |

## Orden de trabajo y evidencias futuras

V3-01 cerrada por el usuario; D01–D06 conservadas como base para sus dependientes.
La inspección visual previa se aplaza hasta M3-02 y no bloquea implementación.
V3-02 cerrada técnicamente: 51 navegador/API y 316 backend PostgreSQL pasan.
Formulario/prueba V3-02 revisados manualmente por el usuario; R02 completado
para la presentación administrativa implementada. V3-03 cerrada técnicamente:
339 backend PostgreSQL y 57 navegador/API pasan, C01–C04 de lectura/contexto
comprobados; sección revocada probada con atenciones longitudinales. Revocaciones
de signos/alergias/notas quedan para V3-04–06, sin secciones simuladas.
V3-04–07 sin iniciar; próxima etapa V3-04. El resto de la aprobación funcional M3-02 sigue pendiente.
Cada etapa registrará comandos/resultados reales en su evidencia y actualizará
plan/ESTADO. Los verificadores V2 existentes y suites PostgreSQL/navegador se
conservan; sus resultados anteriores no prueban los nuevos contratos clínicos.
