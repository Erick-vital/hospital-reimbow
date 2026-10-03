# Estado — Reimbow HIS

Actualizado: 2026-10-03.

## Objetivo activo

V2: interfaz local de Pacientes/Admisión; ejecución y ampliación autorizadas.
Plan activo: [V2 interfaz y admisión](plans/v2-interfaz-admision.md).
Base V1 completa: [plan](plans/v1-base-backend.md), commit `df01151`.
Contrato/ampliación/V2-02A: `a5a592d`; V2-02B guardada en `6e2c926`.
Propuesta: [diseño técnico](docs/propuesta-tecninca.md).

## Avance comprobado

- V1-01–07 completas; [validación](docs/validacion-v1.md) y [guía](docs/desarrollo-v1.md).
- V2-01: contrato/bocetos/matriz y ampliación administrativa aprobada/concretada.
- [Contrato](docs/contrato-v2.md), [campos](docs/campos-v2.md), [bocetos](docs/bocetos-v2.html).
- V2-02A completa: perfiles/listas/desconocido, verificación, ingreso/catálogos/lecturas.
- V2-02B completa: idempotencia PostgreSQL y POST V2 de pacientes/episodios.
- Clave opcional V1/obligatoria V2; replay 200/24 h, reservas vencidas conservadas.
- Concurrencia, rollback, permisos, expiración, pérdida de respuesta y reinicios probados.
- [Evidencia 02A](docs/evidencia-v2-02a.md) y [02B](docs/evidencia-v2-02b.md).
- V2-03 completa: React/TypeScript/Vite/router, lock y proxy dev/preview en loopback.
- Cliente HTTP, identidad/permisos, contextos cancelables y rutas protegidas básicas.
- Build false/true excluye selector/actores/cabecera demo; sin credenciales de base.
- 16 pruebas navegador/API/PostgreSQL y 316 backend pasan, sin fallos ni omisiones.
- Typecheck/npm ci/build comprobados; capturas escritorio/móvil inspeccionadas técnicamente.
- [Guía V2](docs/desarrollo-v2.md), [evidencia 03](docs/evidencia-v2-03.md), [resultados](docs/evidencia/v2-03-resultados.json).
- Node 20.19.5/npm 10.8.2; paquetes y Chromium instalados sólo localmente.
- PostgreSQL 18.6/migraciones 0001–0006; configuración/filas/secuencias previas conservadas.
- APIs/Vite/preview/navegador temporales cerrados; PostgreSQL/volumen conservados.
- Identidad backend apagada por defecto; fixtures nuevas sólo en hospital_test.
- Entrega V2-03 comprobada y guardada en Git; test de auditoría ordenado explícitamente.

## Decisiones vigentes

- PostgreSQL desde el inicio, sin SQLite; FastAPI/Pydantic/SQLAlchemy/Alembic.
- UUID/folios servidor; paciente distinto de episodio/expediente, sin fusión automática.
- Identidad ficticia sólo explícita en desarrollo/test; rechazada en producción.
- Demografía/intake sensibles requieren permisos; replay usa proyección vigente.
- Desconocido sin identidad/nacimiento inventados; rango estimado separado.
- Verificación: nombre más nacimiento/CURP, fuente y actor/fecha servidor; V1 se distingue.
- Ingreso: fecha clínica/sede/servicio/procedencia/motivo; urgencias permite pendientes.
- Ausencia distingue desconocido/no proporcionado/no aplica; known no implica verificado.
- Datos/intenciones sólo en memoria; actor/ruta invalida generación y cancela solicitudes.
- 401/403 limpian/revalidan; recarga pierde actor seleccionado y resuelve acceso de nuevo.
- Búsqueda vence a 15 minutos y no se consume; SEARCH_REQUIRED conserva 422.
- Reserva espera 5 s y restaura timeouts antes del negocio; reservas sin reutilización.
- Prioridad/triage, camas, aseguradoras, cobros, adjuntos y clínica completa diferidos.

## Próximo paso y límites

- Siguiente fase: V2-04, búsqueda/ficha ampliada/episodios; sin bloqueo actual.
- Desarrollo autorizado; no pedir otra confirmación de la misma ampliación.
- V2-04–06 pendientes: buscador/ficha/listas completos, formularios/borradores y A10.
- M2-01 visual humana no ejecutada; M2-02/03 pendientes, capturas no equivalen a aprobación.
- pageshow comprobado con evento de ciclo; sin afirmar restauración bfcache real.
- Sin autenticación real, AWS, aceptación clínica, cumplimiento normativo ni aptitud productiva.

## Mantenimiento

Máximo fijo: 80 líneas y 600 palabras; detalle en plan y docs según [AGENTS.md](AGENTS.md).
