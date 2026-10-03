# Evidencia V1-01 — Entorno y contrato

Fecha: 2026-10-02. Solicitud: implementar la primera etapa del
[plan V1](../plans/v1-base-backend.md). Resultado: entorno revisado, contrato definido
y dependencias resueltas. No hay aplicación ni migraciones ejecutadas.

## Entorno observado

| Comprobación | Resultado |
|---|---|
| Python | CPython 3.12.3, Linux x86_64. |
| pip y venv | pip 24.0; venv creado y pip comprobado en `/tmp/hospital-v1-venv`. |
| Docker CLI/daemon | 29.8.0; `docker info` responde. |
| Docker Compose | v5.5.1. |
| Contenedores activos | Lista vacía en `docker ps`. |
| PostgreSQL host | `psql`, `postgres`, `pg_isready` ausentes del PATH; servidor remoto no comprobado. |
| Estructura inicial | Instrucciones, estado, plan, propuesta y requerimientos; sin backend ni Compose. |
| Git | `git status --short`: no es repositorio operativo; no se inicializó. |
| Procesos | Ningún postgres/uvicorn visible desde el sandbox; visibilidad limitada. |

Socket Docker y DNS de PyPI fueron inicialmente denegados por el sandbox. Las
consultas se repitieron con permiso efectivo y funcionaron. No son fallos de los
productos. No se instalaron componentes del sistema ni paquetes backend; no se
crearon contenedores. El venv temporal sólo comprobó disponibilidad de venv/pip.

Comandos de consulta reproducibles, por separado:

```sh
python3 --version
python3 -m pip --version
command -v docker psql postgres pg_isready
docker --version
docker compose version
docker info --format '{{.ServerVersion}}'
docker ps --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}'
rg --files
git status --short
```

## Versiones y compatibilidad

| Componente directo | Versión fijada |
|---|---|
| Python | 3.12.3, baseline; validar antes de cambiar parche/rama. |
| PostgreSQL | 18.6, elegido para V1-02; sin descargar/ejecutar. |
| FastAPI | 0.142.2 |
| Pydantic / pydantic-settings | 2.13.5 / 2.15.0 |
| SQLAlchemy / Alembic | 2.0.54 / 1.20.0 |
| Psycopg / psycopg-binary | 3.3.6 / 3.3.6 |
| Uvicorn | 0.54.0 |
| pytest / HTTPX | 9.1.1 / 0.28.1 |

Pip resolvió 31 paquetes incluidos los transitivos, con artefactos para CPython
3.12.3/Linux x86_64. [Lock con SHA256](../backend/requirements.lock) y
[metadatos/entorno](evidencia/v1-01-dependencias.json) preservados sin configuración
privada. No prometer reproducción en ARM/macOS. Resolver metadatos no prueba imports,
arranque, migraciones ni conexión. SQLAlchemy síncrono/Psycopg binario evita introducir
otro driver o compilador para este backend local.

Selección inicial ejecutada con resultado 0, sin instalación:

```sh
python3 -m pip --isolated install --dry-run --ignore-installed --no-cache-dir \
  --report /tmp/hospital-v1-resolution.json \
  'fastapi<1' 'pydantic>=2,<3' 'pydantic-settings>=2,<3' \
  'SQLAlchemy>=2.0,<2.1' 'alembic>=1,<2' 'psycopg[binary]>=3,<4' \
  'uvicorn>=0.30,<1' 'pytest>=8,<10' 'httpx>=0.27,<1'
```

Ese comando puede resolver otras versiones en otra fecha. La reproducción usa el lock.
Segunda comprobación ejecutada: resolución del lock y verificación de hashes,
**código 0**, mismas 31 versiones, sin instalar:

```sh
python3 -m venv /tmp/hospital-v1-venv
/tmp/hospital-v1-venv/bin/python -m pip --version
/tmp/hospital-v1-venv/bin/python -m pip --isolated install \
  --dry-run --ignore-installed --no-cache-dir --require-hashes \
  -r backend/requirements.lock --report /tmp/hospital-v1-lock-validation.json
```

Preparación para V1-02 desde la raíz (estos comandos no se ejecutaron):

```sh
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip --isolated install --require-hashes -r backend/requirements.lock
backend/.venv/bin/python -m pip check
```

Fuentes primarias consultadas el 2026-10-02:

- [PostgreSQL 18.6](https://www.postgresql.org/docs/18/release-18-6.html), publicado
  el 2026-08-13, y [soporte](https://www.postgresql.org/support/versioning/).
  Se elige estable soportado frente a 19 beta; imagen/digest por comprobar en V1-02.
- [SQLAlchemy/Psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html):
  dialecto explícito `postgresql+psycopg://`.
- [Psycopg instalación](https://www.psycopg.org/psycopg3/docs/basic/install.html):
  variante binaria para desarrollo sin libpq/compilador del sistema.
- [FastAPI](https://fastapi.tiangolo.com/release-notes/) y metadatos oficiales
  de [PyPI](https://pypi.org/), descargados por pip para las versiones fijadas.

## Contrato y aceptación

[Contrato revisión 1](contrato-v1.md): campos, estados, normalización, restricciones,
tipos, búsqueda previa, proyecciones por permiso, errores, auditoría, ejemplos ficticios
y matriz requisito → criterio de prueba → etapa. Cada requisito seleccionado tiene
criterio; las pruebas funcionales, transaccionales y concurrentes siguen pendientes.

Decisiones: UUID y secuencias de folios independientes; reserva global de
identificadores declarados; verificación inicial por supervisor ficticio; referencia
de búsqueda ligada al actor, vigente 15 minutos. Reconsiderar estas reglas antes de
uso institucional. Similitud avanzada, fusión y verificación posterior diferidas.

Aceptación V1-01: contrato revisable y entorno/dependencias comprobados a este nivel.
No implica aprobación institucional, autenticación real ni operación clínica.
Continuación: V1-02, persistencia, configuración, migraciones y salud.
