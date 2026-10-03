# Estado — Reimbow HIS

Actualizado: 2026-10-03.

## Objetivo activo

V2: interfaz local de Pacientes/Admisión; V2-01–06 completas técnicamente.
Plan activo: [V2](plans/v2-interfaz-admision.md). Revisión funcional pendiente.
V1 backend local completa, commit `df01151`; V2-04 en `45fb1e6`.
[Propuesta técnica](docs/propuesta-tecninca.md), [plan V3 preparado](plans/v3-expediente-basico.md).
V3 solicitada como planificación; implementación todavía no autorizada.

## Avance comprobado

- V1-01–07 completas; [validación](docs/validacion-v1.md) y [guía](docs/desarrollo-v1.md).
- V2-01: contrato/bocetos/matriz y ampliación administrativa aprobada/concretada.
- [Contrato](docs/contrato-v2.md), [campos](docs/campos-v2.md), [bocetos](docs/bocetos-v2.html).
- V2-02A/02B: perfil/contactos/desconocido/verificación/ingreso/catálogos e idempotencia.
- UUID/folios servidor; replay 200/24 h, reservas vencidas conservadas sin reutilización.
- [Evidencia 02A](docs/evidencia-v2-02a.md) y [02B](docs/evidencia-v2-02b.md).
- V2-03/04: frontend/contextos/permisos, búsqueda/ficha/episodios y datos restringidos.
- [Evidencia 03](docs/evidencia-v2-03.md), [04/guion M2-02](docs/evidencia-v2-04.md).
- V2-05: altas ampliadas/desconocido/verificado, confirmación, ingreso y auditoría.
- Búsqueda/evidencia invalidada al cambiar identidad; 409/422 conservan borrador.
- Respuesta perdida conserva cuerpo/clave congelados; otra atención explícita.
- Auditoría HTTP admite catálogos/replay; [evidencia 05](docs/evidencia-v2-05.md).
- V2-06: aviso de recuperación tras recarga/actor, supervisor para desconocido sin folio.
- Teclado/foco/cabecera móvil, timeout después de commit, vencimiento y base inaccesible.
- Concurrencia HTTP simultánea y SQL con barrera/conexiones independientes comprobadas.
- 46 pruebas navegador/API y 316 backend PostgreSQL pasan; ninguna omitida.
- Typecheck/builds false/true sin demo/credenciales; preparación repetida dos veces.
- Migración nueva/repetida/check; filas previas/secuencias/lock/configuración conservados.
- [Evidencia 06/guion M2-03](docs/evidencia-v2-06.md), [resultados](docs/evidencia/v2-06-resultados.json).
- [Guía V2](docs/desarrollo-v2.md) y [matriz](docs/validacion-v2.md).
- Node 20.19.5/npm 10.8.2; dependencias/Chromium existentes, sin instalaciones nuevas.
- PostgreSQL 18.6/0006; fixtures en hospital_test y base aislada de migración conservada.
- Procesos propios de pruebas cerrados; PostgreSQL/sesiones ajenas/volumen conservados.
- Capturas V2-04/05 conservadas e inspeccionadas técnicamente; sin aprobación humana.

## Decisiones vigentes

- PostgreSQL, FastAPI/Pydantic/SQLAlchemy/Alembic; React/TypeScript, monolito modular.
- Paciente distinto de expediente/episodio; sin fusión automática ni datos inventados.
- Identidad demo explícita en desarrollo/test, apagada por defecto y prohibida en producción.
- Demografía/intake por permiso; replay proyecta permisos vigentes y tiene auditoría propia.
- Verificación documentada: nombre más nacimiento/CURP y fuentes; V1 se distingue.
- Urgencias admite pendientes; consulta/hospitalización exige fecha/sede/servicio.
- Ausencias diferenciadas; known no implica verificado; rango estimado no es nacimiento.
- Actor/ruta invalida generación; datos/borradores/intenciones sólo en memoria.
- 401/403 limpian/revalidan; recarga resuelve identidad y descarta intención sin reenviar.
- Búsqueda 15 min; reserva espera 5 s; cliente timeout 10 s, sin reintento automático.
- V3: formularios simples obligatorios y ampliación funcional del MVP.
- Plan V3: atenciones/contexto clínico, signos vitales, alergias, nota en borrador.
- Mejoras administrativas de identidad/trazabilidad aplazadas en propuesta §8.1.

## Próximo paso y límites

- Validación técnica completada; revisión funcional M2-01/02/03 pendiente del usuario.
- V3-01 sólo tras autorización de implementación; contrato/roles/diseño por precisar.
- V3 no tiene etapas implementadas; plan preparado no implica aceptación clínica.
- Base inaccesible en API propia; reinicio físico previo V2-02B, sin interrupción compartida.
- pageshow probado con evento; sin afirmar bfcache real. Tiempos sin SLA/carga.
- Sin autenticación real, AWS, firma clínica ni aptitud productiva.

## Mantenimiento

Máximo fijo: 80 líneas y 600 palabras; detalle en plan y docs según [AGENTS.md](AGENTS.md).
