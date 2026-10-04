# Estado — Reimbow HIS

Actualizado: 2026-10-03.

## Objetivo activo

V3: expediente básico y formularios simples; V3-03 cerrada técnicamente.
Plan activo: [V3](plans/v3-expediente-basico.md).
V3-03 implementada por autorización explícita; V3-04–07 sin iniciar.
Formulario/prueba V3-02 revisados por el usuario; resto de M3-02 pendiente.
[Propuesta técnica](docs/propuesta-tecninca.md).

## Avance comprobado

- V1 backend local completa (`df01151`); [validación](docs/validacion-v1.md).
- V2-01–06 completas técnicamente, commit `cc86c8e`; revisiones humanas pendientes.
- [Plan V2](plans/v2-interfaz-admision.md), [validación](docs/validacion-v2.md),
  [evidencia 06](docs/evidencia-v2-06.md).
- V3-01 cerrada por el usuario: contrato/diseño acotados; 21 comprobaciones
  del boceto y capturas inspeccionadas técnicamente, sin aceptación funcional.
- [Contrato V3](docs/contrato-v3.md), [matriz](docs/validacion-v3.md).
- V3-02: captura directa, razones/listas, descarte confirmado y resumen;
  [evidencia](docs/evidencia-v3-02.md): 51 navegador/API y 316 backend pasan.
- V3-03: atenciones abiertas paginadas y filtros; contexto por episodio/paciente,
  cabecera PAC/EPI permanente, permisos explícitos y auditoría transaccional.
- [Evidencia V3-03](docs/evidencia-v3-03.md), [guía](docs/desarrollo-v3.md):
  339 backend PostgreSQL y 57 navegador/API pasan; TypeScript/build correctos.
- C01–C04 del alcance implementado comprobados: semilla/revocaciones, filtros,
  proyección, contexto/actor/atrás/recarga/respuestas tardías, auditoría y móvil.
- Regresión V1/V2 conserva reintentos, pérdida de respuesta, concurrencia y permisos.
- PostgreSQL 18.6/migración 0007; Node 20.19.5/npm 10.8.2 existentes.
- Migración/semilla aplicadas en hospital_test/hospital_dev: seis actores,
  cinco roles y doce permisos. Identidad demo conserva habilitación explícita.
- Sin instalaciones, despliegue, configuración modificada ni borrado de datos.
- Ejecuciones afectadas por sandbox repetidas fuera con permiso efectivo;
  runner cerró servicios propios. Fixtures ficticias conservadas en hospital_test.
- Trabajo V3-01–03 consolidado en el commit de cierre de esta entrega.

## Decisiones vigentes

- PostgreSQL, FastAPI/Pydantic/SQLAlchemy/Alembic; React/TypeScript, monolito modular.
- Paciente, expediente y episodio distintos; UUID/folios servidor, sin fusión automática.
- Demo explícito development/test, apagado por defecto, prohibido en producción.
- Admisión/Supervisor con listas administrativas explícitas; Consulta sin ampliación.
- Médico/Enfermería: lectura básica y tres permisos clínicos de lectura implementados;
  clínica demo global, sin asignaciones ni rótulo «mis pacientes».
- Proyección clínica limitada; no demografía/intake completos ni evidencia de identidad.
- Semilla repetida conserva UUID, suspensiones y permisos/asignaciones revocados.
- V3: signos/notas por episodio, alergias longitudinales; nota sólo borrador no firmado.
- D01 aplicada; D02–D06 base revisable al final, sin umbrales/alertas inventados.
- Mejoras administrativas aplazadas en propuesta §8.1; garantías V2 conservadas.

## Pendiente y próximo paso

- Próxima etapa V3-04: signos vitales; requiere autorización de implementación.
- V3-04–07 sin implementar; no hay secciones clínicas simuladas en V3-03.
- C04 de signos/alergias/notas se comprobará al añadir sus permisos/secciones.
- Revisar restantes vistas/decisiones clínicas al final en M3-02; pendiente.
- V2 conserva M2-01/02/03 pendientes; sin observaciones nuevas.
- Sin autenticación real, AWS, firma ni aptitud clínica/productiva.

## Mantenimiento

Máximo fijo: 80 líneas y 600 palabras; detalle en plan/docs según [AGENTS.md](AGENTS.md).
