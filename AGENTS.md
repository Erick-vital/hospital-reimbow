# Instrucciones para agentes — Proyecto hospital

## Ámbito

Estas instrucciones aplican a `/home/tao/repos/proyecto-hospital` y sus descendientes. Este proyecto es Reimbow HIS; las decisiones de locomoción de otros directorios no se aplican aquí. Responder en español y trabajar dentro de la tarea autorizada.

## Retomar trabajo

1. Leer `ESTADO.md` y el plan activo indicado allí.
2. Consultar `docs/propuesta-tecninca.md` y sólo los requerimientos pertinentes.
3. Revisar archivos, cambios existentes y procesos antes de asumir que algo está implementado o sigue ejecutándose.

El plan define alcance y aceptación; el estado indica dónde continuar; los requerimientos conservan la intención funcional. Priorizar correcciones explícitas recientes del usuario y registrar discrepancias. No confundir documentación preparada con implementación autorizada o terminada.

## Política de tamaño fijo de ESTADO.md

`ESTADO.md` es un resumen operativo con presupuesto fijo: **máximo 80 líneas y máximo 600 palabras**, incluidos encabezados y listas. Ambos límites deben cumplirse. No rellenar hasta el máximo ni aumentar los límites sin instrucción del usuario.

Conservar únicamente objetivo/versión activa, decisiones vigentes, avance comprobado, bloqueo actual, próximo paso y referencias necesarias. Actualizar reemplazando contenido obsoleto; no añadir un diario acumulativo ni copiar logs, requerimientos o planes completos.

Antes de una actualización que exceda el límite, condensar el estado y trasladar historial/evidencia al plan activo o a un documento pertinente en `docs/`. Mantener enlaces a ese detalle. Comprobar líneas y palabras después de cada edición; superar cualquiera de los límites impide dar por terminada la actualización documental.

Actualizar plan y estado al cerrar una etapa, cambiar una decisión, identificar un bloqueo o dejar una prueba preparada. En trabajos largos, guardar hitos útiles sin ampliar el estado. No hace falta modificar documentos por una conversación que no cambie decisiones o ejecución.

## Arquitectura y alcance

- PostgreSQL desde el inicio, también para integración; SQLite descartado.
- Backend propuesto: FastAPI, Pydantic, SQLAlchemy y Alembic; monolito modular.
- Separar rutas, reglas de negocio, autorización y persistencia; cambios sensibles y auditoría de éxito comparten transacción.
- Mantener migraciones reproducibles y restricciones de base para integridad y concurrencia.
- Aplicar el alcance de `plans/v1-base-backend.md`: V1 local, sin Cognito, AWS, frontend ni flujos clínicos completos.
- No crear contraseñas propias como atajo. La identidad simulada de V1 sólo puede existir con habilitación explícita en desarrollo/pruebas y debe rechazarse en producción.
- La autenticación futura no sustituye permisos, privilegios y asignaciones internos ni la firma clínica.

## Integridad y seguridad

Usar sólo datos ficticios en desarrollo/pruebas. No incluir secretos, tokens o información clínica real en documentación, logs o ejemplos. Proteger identidad y campos según permisos del servidor.

Paciente, expediente y episodio son conceptos distintos. No usar CURP/correo como llave interna ni inventar datos faltantes de urgencia. No implementar eliminación ordinaria de pacientes o episodios con actividad.

En futuras versiones clínicas: notas firmadas conservan original y correcciones trazables; autor y supervisor son distintos; propuestas pendientes no son ejecutables; inventario se explica por movimientos y los cambios concurrentes requieren comprobación transaccional.

## Evidencia y permisos

No marcar etapas completas sin comprobaciones del criterio de aceptación. Registrar comandos reproducibles, resultados y limitaciones en documentos pertinentes; enlazarlos desde el plan. Distinguir propuestas, decisiones confirmadas y mediciones.

Probar servicios y flujos afectados; integración sobre PostgreSQL. No sustituir una prueba concurrente por dos operaciones secuenciales. No afirmar cumplimiento normativo, firma válida o preparación productiva por tener endpoints.

Conservar documentos originales y revisar archivos existentes antes de editar. No tocar temporales del editor. No instalar, desplegar, contratar servicios ni ejecutar cambios del sistema por el solo hecho de que figuren en un plan; respetar autorización vigente y permisos efectivos del entorno. Una vez solicitada implementación, avanzar en los pasos normales autorizados sin pedir confirmación repetida.
