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
- V2-03 completa y guardada en Git: frontend base/contextos/permisos y builds sin demo.
- [Guía V2](docs/desarrollo-v2.md) y [evidencia 03](docs/evidencia-v2-03.md).
- V2-04 completa técnicamente: filtros/paginación/selección, ficha ampliada y episodios.
- Calidad documentada/V1 sin evidencia, ausencias y desconocido sin datos inventados.
- Demografía/intake por permiso; PAC/EPI separados y cabecera visible al desplazarse.
- Consultas atrasadas descartadas; recarga/URL/401/403/404 y storage vacío probados.
- 26 pruebas navegador/API/PostgreSQL y 316 backend pasan, sin fallos ni omisiones.
- Typecheck/build false/true sin demo/credenciales; lock/configuración/filas previas conservados.
- [Evidencia/guion M2-02](docs/evidencia-v2-04.md), [resultados](docs/evidencia/v2-04-resultados.json).
- Capturas escritorio/móvil inspeccionadas técnicamente; sin revisión humana.
- Node 20.19.5/npm 10.8.2; dependencias/Chromium locales de V2-03 conservados.
- PostgreSQL 18.6/migraciones 0001–0006; fixtures ficticias nuevas sólo en hospital_test.
- APIs/Vite/preview/navegador temporales cerrados; PostgreSQL/volumen conservados.
- Identidad backend apagada por defecto; sin cambios del sistema ni instalaciones nuevas.

## Decisiones vigentes

- PostgreSQL desde el inicio, sin SQLite; FastAPI/Pydantic/SQLAlchemy/Alembic.
- UUID/folios servidor; paciente distinto de episodio/expediente, sin fusión automática.
- Identidad ficticia sólo explícita en desarrollo/test; rechazada en producción.
- Demografía/intake sensibles requieren permisos; replay usa proyección vigente.
- Desconocido sin identidad/nacimiento inventados; rango estimado separado.
- Verificación: nombre más nacimiento/CURP, fuente y actor/fecha servidor; V1 se distingue.
- Ingreso: fecha clínica/sede/servicio/procedencia/motivo; urgencias permite pendientes.
- Ausencia distingue desconocido/no proporcionado/no aplica; known no implica verificado.
- Filtro desconocido sólo V2 explícito; sede/servicio conocidos muestran UUID, sin ampliar permisos.
- Datos/intenciones sólo en memoria; actor/ruta invalida generación y cancela solicitudes.
- 401/403 limpian/revalidan; recarga pierde actor seleccionado y resuelve acceso de nuevo.
- Búsqueda vence a 15 minutos y no se consume; SEARCH_REQUIRED conserva 422.
- Reserva espera 5 s y restaura timeouts antes del negocio; reservas sin reutilización.
- Prioridad/triage, camas, aseguradoras, cobros, adjuntos y clínica completa diferidos.

## Próximo paso y límites

- Siguiente fase: V2-05, registro ampliado/apertura idempotente; sin bloqueo técnico.
- Desarrollo autorizado; no pedir otra confirmación de la misma ampliación.
- V2-05/06 pendientes: formularios/borradores, auditoría visual, recuperación y A10.
- M2-01 visual no ejecutada; M2-02 preparada sin respuesta humana, M2-03 pendiente.
- pageshow comprobado con evento de ciclo; sin afirmar restauración bfcache real.
- Sin autenticación real, AWS, aceptación clínica, cumplimiento normativo ni aptitud productiva.

## Mantenimiento

Máximo fijo: 80 líneas y 600 palabras; detalle en plan y docs según [AGENTS.md](AGENTS.md).
