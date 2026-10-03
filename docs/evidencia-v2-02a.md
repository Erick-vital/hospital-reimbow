# Evidencia V2-02A — Backend administrativo ampliado

Fecha: 2026-10-03. Ejecutada por solicitud «continua con la sig fase de v2».
Resultado: A01–A08 comprobados en esquemas, servicios sobre PostgreSQL y lecturas
HTTP. **276 pruebas pasan, sin fallos ni omisiones**. [Resultados estructurados](evidencia/v2-02a-resultados.json).
Plan: [V2](../plans/v2-interfaz-admision.md); contrato: [revisión 2](contrato-v2.md).

## Implementación comprobada

- Migración `0005` y siete tablas nuevas: perfil administrativo, elementos de
  teléfonos/domicilios/contactos, verificación, evidencia por campo, sedes,
  servicios e intake. Estados/escalares JSONB con CHECK de forma/valor; listas en
  filas subordinadas con posición 0–9, PK por paciente/tipo/posición.
- FK RESTRICT, pareja sede/servicio, rango estimado y coherencia state/value.
  Constraint triggers diferidos comprueban identidad/desconocido, evidencia exacta,
  cardinalidad y estado al commit. La evidencia no se puede reasignar dejando
  incompleta la verificación del paciente original.
- Verificación de nombre más nacimiento o CURP; instantáneas normalizadas, actor
  interno y fecha UTC de PostgreSQL. Datos TEST/referidos no justifican verified.
- Ingreso con zona/UTC, fecha clínica separada de registro y validación por tipo;
  urgencia acepta pendientes. Catálogos activos/coherentes comprobados con bloqueo
  de filas compartido durante escritura; suspensiones no alteran ingresos históricos.
- Semilla ficticia y permiso `admissions.read_intake` en la misma transacción
  de identidad. Repeticiones conservan UUID, nombres, suspensiones y filas ajenas.
- GET V2 de búsqueda/ficha/episodio/lista y catálogos, paginación/autorización,
  proyecciones explícitas, correlación, auditoría y `Cache-Control: no-store`.
  Calidad básica sin fuentes; datos ampliados omitidos sin permiso correspondiente.
- Reutilización de búsqueda, reservas de identificadores, secuencias y creación
  V1 dentro de servicios transaccionales. Evidencia/recurso/auditoría se revierten
  juntos si falla cualquier parte. Auditoría conserva sus listas explícitas V1:
  fuentes, descriptores e intake no se vuelcan en logs/metadatos arbitrarios.

## Comandos ejecutados

Desde la raíz, con el entorno virtual existente; no se instalaron paquetes:

```sh
docker compose --env-file backend/.env up -d --wait postgres
backend/.venv/bin/python backend/scripts/verify_v2_02a.py --baseline-only /tmp/reimbow-v2-02a-baseline.json
backend/.venv/bin/python backend/scripts/prepare_local.py
backend/.venv/bin/python backend/scripts/verify_v2_02a.py --baseline /tmp/reimbow-v2-02a-baseline.json
```

Para repetir desde el estado actual sin depender del archivo temporal:

```sh
backend/.venv/bin/python backend/scripts/verify_v2_02a.py
```

El verificador prepara dos veces desarrollo/pruebas, compara hashes de filas y
secuencias, mantiene `.env`/modo 600, migra una base aislada desde cero con upgrade
repetido/Alembic check, ejecuta toda la suite y abre/cierra una API TCP temporal en
loopback contra `hospital_test`. No genera logs de acceso, HAR ni datos clínicos reales.
La referencia temporal contiene hashes y secuencias, sin cuerpos demográficos;
acredita la transición de esta sesión desde 0004, no se reconstruye en otra ejecución.

## Resultados y preservación

Punto de partida: PostgreSQL detenido, sin API activa, revisión 0004. Se arrancó
el contenedor/volumen existente. En `hospital_test` se preservaron las 1,042 filas
de pacientes, 1,016 identificadores, 1,380 búsquedas, 21 episodios y 2,701 eventos
previos; UUID/folios/fechas/autores y secuencias no se reiniciaron. Desarrollo
conservó sus identidades; antes de migrar no tenía pacientes ni episodios.
Filas V1 sin perfil/intake se proyectan como `legacy` y `not_provided`; no se
fabricaron fechas clínicas, declaraciones de desconocido ni evidencia documental.

La corrida final verificó una base nueva conservada:
`hospital_v2_validation_981ac69d281d4a599b30b43a77ffd040`.
La corrida anterior conservó también `hospital_v2_validation_6ac2573f3bd44372aade31b97f11d56d`.
Ambas son bases aisladas locales sin API/identidad simulada productiva; no se borraron.
Las pruebas concurrentes de regresión V1 y las sondas HTTP conservan nuevas filas
ficticias en `hospital_test`; los casos con savepoints revierten sus filas.

| Caso | Evidencia ejecutada |
|---|---|
| A01 | Listas múltiples/ausencia, extranjeros, normalización/límites, contactos y domicilio vacío; persistencia subordinada. |
| A02 | Desconocido explícito sin descriptores/con rango; rechazo de identidad inventada/contradicciones. Búsqueda V2 explícita y V1 conservada. |
| A03 | Nombre+nacimiento y nombre+CURP; instantáneas/fuentes/actor/fecha; constraint triggers comprobados también en los casos válidos. |
| A04 | Permiso previo, campos extra rechazados, fallos reales de evidencia/auditoría y rollback completo. |
| A05 | Catálogos paginados, semilla repetida/suspensiones; FK y pareja incorrecta rechazadas con SQL. |
| A06 | UTC, fecha pasada/distinta de registro, urgencia pendiente; mínimos de consulta/hospitalización y SQL directo. |
| A07 | JSON básico omite demografía/intake; permiso de campos solo no concede lectura; 401/403/404 y auditoría. |
| A08 | Declaración verified V1 sin evidencia distinguida; ausencia/origen legacy; respuestas V1 y filas previas conservadas. |

Suite: [pruebas ampliadas](../backend/tests/test_administrative_v2.py) más regresión
V1 completa. Los casos con savepoints fuerzan `SET CONSTRAINTS ALL IMMEDIATE`
para comprobar integridad diferida; las sondas HTTP usan servicios con commits reales.
API real: 14 solicitudes de lectura/denegación con correlación y auditoría comprobadas,
verificado documentado, ingreso UTC, proyecciones de supervisor/consulta y catálogos.

Versiones medidas: Python 3.12.3; PostgreSQL 18.6; FastAPI 0.142.2;
Pydantic 2.13.5; SQLAlchemy 2.0.54; Alembic 1.20.0; psycopg 3.3.6;
pytest 9.1.1; Uvicorn 0.54.0. Una advertencia de deprecación del TestClient
Starlette/httpx permanece; no se cambiaron dependencias por ella.

Durante el desarrollo se corrigieron el nombre de restricciones Alembic,
el rechazo de state=null y la reasignación de evidencia. Las funciones 0005
de las dos bases existentes se sincronizaron sin cambiar filas; la corrida final
desde cero usa directamente la migración corregida. La evidencia final corresponde
al código corregido. Los resultados históricos V1 no se sobrescribieron.

## Límites y continuación

POST V2 no publicado: `/api/v2/patients` rechaza POST con 405 y
`/api/v2/admissions` aún no existe como ruta de alta. Los servicios de escritura
se prueban directamente; publicación/idempotencia siguen en V2-02B. Sin frontend,
revisión visual, autenticación real, edición, clínica completa ni validación productiva.
PostgreSQL permanece activo en loopback; procesos API propios cerrados;
identidad simulada apagada por defecto. Cambios anteriores conservados; sin commit.
