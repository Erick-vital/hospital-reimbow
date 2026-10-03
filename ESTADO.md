# Estado — Reimbow HIS

Actualizado: 2026-10-03.

## Objetivo activo

V2: interfaz local de Pacientes/Admisión; ejecución y ampliación autorizadas.
Plan activo: [V2 interfaz y admisión](plans/v2-interfaz-admision.md).
Base completada: [V1 backend](plans/v1-base-backend.md), commit `df01151`.
Contrato/ampliación/V2-02A guardados por solicitud en commit `a5a592d`.
Propuesta: [diseño técnico](docs/propuesta-tecninca.md).

## Avance comprobado

- V1-01–07 completas; [validación](docs/validacion-v1.md) y [guía](docs/desarrollo-v1.md).
- V2-01: contrato/bocetos/matriz y ampliación administrativa aprobada/concretada.
- [Contrato revisión 2](docs/contrato-v2.md), [campos](docs/campos-v2.md), [bocetos](docs/bocetos-v2.html).
- [Matriz/comandos](docs/validacion-v2.md); [decisiones V2-01](docs/evidencia-v2-01.md).
- V2-02A completa: perfiles/listas/desconocido, verificación, ingreso y catálogos.
- Lecturas V2 y permisos/correlación/auditoría; [evidencia 02A](docs/evidencia-v2-02a.md).
- V2-02B completa: idempotencia PostgreSQL y POST V2 de pacientes/episodios.
- Clave opcional V1/obligatoria V2, replay 200/24 h, reservas vencidas conservadas.
- Concurrencia con barrera/conexiones distintas, rollback, permisos y expiración probados.
- Respuesta perdida después del commit y reinicios API/PostgreSQL recuperan mismo recurso.
- I01–I13/A09/R01: 316 pruebas pasan, sin fallos ni omisiones; espera HTTP 5.011 s.
- [Evidencia/comandos 02B](docs/evidencia-v2-02b.md); [resultados](docs/evidencia/v2-02b-resultados.json).
- PostgreSQL 18.6, migraciones 0001–0006; desde cero y desde 0005 con datos comprobadas.
- UUID/folios/fechas/autores/filas/secuencias previas conservados; upgrade/check repetidos.
- PostgreSQL en loopback/volumen conservado; APIs temporales cerradas; identidad apagada.
- Node 20.19.5/npm 10.8.2; sin frontend instalado ni lock/build.
- Cambios V2-02B comprobados y pendientes de commit; bases ficticias conservadas.

## Decisiones vigentes

- PostgreSQL desde el inicio, sin SQLite; FastAPI/Pydantic/SQLAlchemy/Alembic.
- UUID/folios servidor; paciente distinto de episodio/expediente, sin fusión automática.
- Identidad ficticia sólo explícita en desarrollo/test; rechazada en producción.
- Sexo registrado/nacionalidad, teléfonos/domicilios/contactos múltiples.
- Desconocido: descriptores/rango estimado/traslado; sin inventar nacimiento/identidad.
- Ingreso: fecha clínica/sede/servicio/procedencia/motivo; urgencias permite pendientes.
- Verificación: nombre más nacimiento/CURP, fuente y actor/fecha servidor.
- Declaraciones V1 sin evidencia se distinguen; /api/v2 conserva esquemas V1.
- Demografía/intake sensibles requieren permisos; replay usa proyección vigente.
- Ausencia distingue desconocido/no proporcionado/no aplica; known no implica verificado.
- React/TypeScript, proxy local/loopback; datos/intenciones sólo en memoria navegador.
- Búsqueda vence a los 15 minutos y no se consume; SEARCH_REQUIRED conserva 422.
- Reserva espera 5 s; restaura lock_timeout/statement_timeout antes del negocio.
- Prioridad/triage, camas, aseguradoras, cobros, adjuntos y clínica completa diferidos.

## Próximo paso y límites

- Siguiente fase: V2-03, base frontend e identidad local; sin bloqueo actual.
- Desarrollo autorizado; no pedir otra confirmación de la misma ampliación.
- V2-03–06, navegador/A10 y M2-02/03 pendientes; revisión visual M2-01 no ejecutada.
- POST V2 operativo localmente; sin autenticación real, AWS ni clínica completa.
- Para verificar backend vigente usar verify_v2_02b.py; 02A conserva guion histórico.
- Sin cumplimiento normativo ni preparación productiva afirmados.

## Mantenimiento

Máximo fijo: 80 líneas y 600 palabras; detalle en plan y docs según [AGENTS.md](AGENTS.md).
