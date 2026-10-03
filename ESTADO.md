# Estado — Reimbow HIS

Actualizado: 2026-10-02.

## Objetivo activo

V1: base backend local con FastAPI y PostgreSQL, completada V1-01–07.
Solicitud vigente: continuar la siguiente fase; V1-07 validación/entrega terminada.
Plan: [V1 base backend](plans/v1-base-backend.md).
Propuesta: [diseño técnico](docs/propuesta-tecninca.md).

## Avance comprobado

- 21 Markdown de requerimientos; originales conservados, seis con contenido.
- 119 RF y 58 RNF identificados; quince documentos originales vacíos.
- Python 3.12.3, 31 dependencias con hashes; Docker/Compose disponibles.
- PostgreSQL 18.6 local persistente; desarrollo/pruebas con usuarios separados.
- Migraciones 0001–0004; base nueva completa y Alembic check sin divergencias.
- Semilla idempotente: cuatro actores, tres roles y ocho permisos explícitos.
- Pacientes: búsqueda paginada, alta provisional/verificada y lecturas autorizadas.
- Búsqueda previa ligada a actor/datos/vigencia; reserva global UNIQUE de identificadores.
- Desconocidos sin CURP/nacimiento/nombre inventados; UUID/folios independientes.
- Episodios open de tres tipos; autor/fecha servidor, múltiples por paciente y listado.
- Cambios/auditoría atómicos; denegaciones aparte y FK restrictivas.
- 199 pruebas pasan sin omisiones: restricciones, rollback y concurrencia con barrera.
- HTTP real: búsqueda → paciente → episodio → lectura/listado, 401/403 y auditoría.
- Preparación repetida conserva .env (600), todas las filas y secuencias.
- Reinicio conserva ambas bases y entidades; mismo proceso API recupera su pool.
- Diagnóstico: 1.000 pacientes nuevos, 300 búsquedas medidas y cero errores.
- p95 folio/nombre/TEST: 10,347/15,185/10,783 ms, concurrencia 1, sin SLA.
- [Evidencia V1-07](docs/evidencia/v1-07-resultados.json) y [validación](docs/validacion-v1.md).
- [Guía reproducible](docs/desarrollo-v1.md); PostgreSQL activo, APIs temporales cerradas.

## Decisiones vigentes

- PostgreSQL desde el inicio; SQLite descartado. Imagen fijada por digest.
- FastAPI/Pydantic/SQLAlchemy/Alembic, monolito modular y Psycopg 3 síncrono.
- Folios por secuencias sin reinicio/reutilización; reserva no confirma identidad.
- [Contrato revisión 4](docs/contrato-v1.md); sin fusión automática.
- Identidad ficticia sólo explícita en desarrollo/test; apagada por defecto.
- V1 excluye autenticación real, Cognito, AWS, frontend y clínica completa.

## Próximo paso y límites

- V1 no tiene otra fase pendiente; revisión funcional reproducible con la guía.
- Definir y autorizar el alcance de la siguiente versión antes de implementarla.
- Sin idempotencia de POST, edición/borrado, firma ni supervisión avanzada.
- Rendimiento medido sólo local; gran volumen/capacidad productiva no acreditados.
- Warning TestClient/HTTPX documentado; lock vigente funciona.
- Sin bloqueo actual ni aprobación manual afirmada. Git local inicializado para V1.
- Datos ficticios conservados en hospital_test; .env privado en backend/.
- Dos bases aisladas de validación conservadas (una vacía de intento corregido).

## Mantenimiento

Máximo fijo: 80 líneas y 600 palabras; detalle en plan y docs según [AGENTS.md](AGENTS.md).
