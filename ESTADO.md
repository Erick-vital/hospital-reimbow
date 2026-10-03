# Estado — Reimbow HIS

Actualizado: 2026-10-03.

## Objetivo activo

V2: interfaz local de Pacientes/Admisión; ejecución y ampliación autorizadas.
Usuario aprobó recomendación administrativa con «ok hazlo entonces».
Plan activo: [V2 interfaz y admisión](plans/v2-interfaz-admision.md).
Base completada: [V1 backend](plans/v1-base-backend.md), commit `df01151` en main.
Propuesta: [diseño técnico](docs/propuesta-tecninca.md).

## Avance comprobado

- V1-01–07 completas; 199 pruebas y recorrido HTTP comprobados en V1.
- PostgreSQL 18.6, migraciones 0001–0005, semilla/permisos y auditoría transaccional.
- [Validación V1](docs/validacion-v1.md) y [guía](docs/desarrollo-v1.md) conservadas.
- V2-01: contrato/bocetos/matriz preparados; ampliación aprobada y concretada.
- [Contrato revisión 2](docs/contrato-v2.md), [campos/reglas](docs/campos-v2.md), [bocetos](docs/bocetos-v2.html).
- [Matriz/comandos](docs/validacion-v2.md) y [evidencia/decisiones](docs/evidencia-v2-01.md).
- Node 20.19.5/npm 10.8.2; compatibilidad declarada de herramientas consultada.
- V2-02A completada: perfiles/listas/desconocido, evidencia, ingreso y catálogos.
- Lecturas V2 con permisos/correlación/auditoría; POST V2 pendiente de idempotencia.
- A01–A08 y regresión V1: 276 pruebas pasan; HTTP real/base nueva comprobados.
- [Evidencia/comandos V2-02A](docs/evidencia-v2-02a.md) y [resultados](docs/evidencia/v2-02a-resultados.json).
- Filas/folios/fechas/autores V1 conservados; upgrade repetido/check sin divergencias.
- PostgreSQL activo en loopback, volumen conservado; API temporal cerrada.
- Sin frontend instalado ni lock/build; bases de validación ficticias conservadas.

## Decisiones vigentes

- PostgreSQL desde el inicio, sin SQLite; FastAPI/Pydantic/SQLAlchemy/Alembic.
- UUID/folios servidor; paciente distinto de episodio/expediente, sin fusión automática.
- Identidad ficticia sólo explícita en desarrollo/test; apagada por defecto.
- V2 incorpora sexo registrado/nacionalidad, teléfonos/domicilios/contactos múltiples.
- Desconocido: descripción, rango estimado y traslado; sin inventar nacimiento/identidad.
- Ingreso: fecha clínica, sede/servicio, procedencia y motivo; urgencias permite pendientes.
- Verificación: nombre más nacimiento/CURP contrastados, fuente y actor/fecha servidor.
- Declaraciones V1 sin evidencia se distinguen; rutas ampliadas /api/v2 conservan V1.
- Proyecciones demográficas e intake sensibles requieren permisos explícitos.
- Ausencia distingue desconocido/no proporcionado/no aplica; known no significa verificado.
- React/TypeScript, proxy local y loopback; datos/intenciones sólo en memoria navegador.
- Clave opcional API V1, obligatoria V2; replay 200/24 h, reservas sin reutilización.
- Búsqueda previa V1 vence a los 15 minutos; no se consume en alta.
- Prioridad/triage, camas, aseguradoras, cobros, adjuntos y clínica completa diferidos.

## Próximo paso y límites

- Siguiente fase: V2-02B, idempotencia PostgreSQL y publicación de POST V2.
- Claves/versiones/replay/expiración, permisos actuales y concurrencia real por comprobar.
- Continuar desarrollo autorizado sin otra confirmación de la misma ampliación.
- Revisión visual de M2-01 no ejecutada; M2-02/03 pendientes.
- V2-02B–06 pendientes; frontend y recorrido HTTP de alta V2 aún no operativos.
- V1 sigue sin idempotencia; altas V2 sólo por servicios transaccionales comprobados.
- Cobertura administrativa parcial; sin cumplimiento normativo ni preparación productiva afirmados.
- Cambios previos conservados; sin commit solicitado/realizado.

## Mantenimiento

Máximo fijo: 80 líneas y 600 palabras; detalle en plan y docs según [AGENTS.md](AGENTS.md).
