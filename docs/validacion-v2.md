# Validación V2 — matriz y comandos

Fecha: 2026-10-03. A01–A08 comprobados en V2-02A; I01–I13/A09/R01 en V2-02B.
316 pruebas backend pasan y altas/replay/reinicios HTTP reales comprobados.
V2-03 añade 16 pruebas de navegador de identidad/contextos/rutas: [evidencia](evidencia-v2-03.md).
[Evidencia 02A](evidencia-v2-02a.md), [evidencia 02B](evidencia-v2-02b.md) y
[resultados vigentes](evidencia/v2-02b-resultados.json). Recorrido de búsqueda/altas pendiente.
Contrato: [revisión 2](contrato-v2.md) y [campos ampliados](campos-v2.md).
Evidencia V1 conservada en [validación V1](validacion-v1.md).

## Entorno y ejecución

Sólo datos ficticios; base `hospital_test` y usuario distinto al de `hospital_dev`.
Pruebas backend sobre PostgreSQL, nunca SQLite. Pruebas navegador contra API real
con `APP_ENV=test`; no sustituirla por respuestas mock para aceptación del recorrido.
Casos negativos de identidad usan proceso API separado, modo apagado o producción.
No restaurar permisos sembrando indiscriminadamente; revertir cambios de cada prueba.
Casos que necesitan commits (HTTP/concurrencia/reinicio) usan identificadores TEST
únicos por ejecución y conservan las entidades, sin borrar pacientes/episodios ni
reiniciar secuencias. Registrar UUID/folios ficticios en evidencia pertinente.

Comandos existentes de backend, desde raíz; ejecutar tras implementar migración V2:

```sh
docker compose --env-file backend/.env up -d --wait
APP_ENV=test backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
APP_ENV=test backend/.venv/bin/python -m alembic -c backend/alembic.ini check
backend/.venv/bin/python -m pytest -q -c backend/pyproject.toml backend/tests
APP_ENV=test DEV_IDENTITY_ENABLED=true backend/.venv/bin/python -m uvicorn hospital.main:create_app --factory --app-dir backend/src --host 127.0.0.1 --port 8001 --no-access-log
```

También aplicar/consultar migraciones en una base nueva aislada como V1-07 y repetir
upgrade sin cambios. No interpretar `upgrade head` de una base existente como prueba
de instalación desde cero. Migraciones de desarrollo se aplicarán sólo en su etapa,
conservando datos y configuración. Reinicio controlado del servicio del proyecto
requiere coordinar ausencia de sesiones; conservar/restaurar servicio en `finally`.

Scripts frontend V2-03 implementados; comandos desde `frontend/`:

```sh
cd frontend
npm ci
npm run typecheck
npm run build
VITE_DEMO_IDENTITY=true npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
V2_API_PORT=8001 npm run test:e2e
```

`test:e2e` levanta frontend/API propios tras validar `hospital_test` y usuario
separado antes de escribir fixtures; cierra sus procesos. `V2_API_PORT` fija el
puerto local del proxy/API de pruebas propia; no es una variable backend.
Proxy `/api` sin reescribir el prefijo, target loopback; build se prueba además con
modo demo apagado. Vite preview no sustituye automáticamente el proxy de desarrollo:
V2-03 configura y prueba proxy de preview explícitamente.
Dependencias locales y Chromium ya instalados/comprobados en V2-03.
No usar `playwright install --with-deps` para modificar el sistema implícitamente.
Desactivar traces/HAR/vídeos y logs de acceso; evidencias con datos exclusivamente ficticios.

## Casos de aceptación

Distribución de V2-02: A01–A08 comprobados en V2-02A mediante esquemas/servicios
sobre PostgreSQL y rutas HTTP de lectura. POST V2 publicados y comprobados
con idempotencia en V2-02B, junto con I01–I13, A09 y R01. A10 requiere frontend y continúa en V2-05/06.
Plan detallado y aceptación por hito: [V2](../plans/v2-interfaz-admision.md).

| Caso | Prueba y resultado exigido | Fase / origen |
|---|---|---|
| A01 | Perfil, teléfonos/domicilios/contactos múltiples; límites, extranjeros, componentes vacíos y contacto sin nombre; known/null y razones de ausencia coherentes. | V2-02A; Pacientes §5/8–10 |
| A02 | Desconocido con todos los descriptores ausentes y con rango estimado válido; sin nombre/nacimiento inventados, rangos incoherentes rechazados y sexo aparente separado de registrado. | V2-02A; Pacientes §13, Admisión §9 |
| A03 | verified con nombre+nacimiento o nombre+CURP, fuentes/documento/actor/fecha; rechazar sólo nombre, TEST/folio como segundo, duplicados y evidencia que no corresponda. | V2-02A; Pacientes §6–7, Admisión §8 |
| A04 | Actor sin verify_identity no crea verificado aun con evidencia; campos servidor rechazados; fallo de evidencia/auditoría revierte todo. | V2-02A; permisos/transacción |
| A05 | Sede/servicio activo y coherente; FK y pareja protegidas en SQL directo; semilla repetida conserva datos/suspensiones. | V2-02A; Admisión §10 |
| A06 | admitted_at con zona normalizado a UTC, distinto de created_at; futuro/sin zona rechazado. emergency abre con pendientes; outpatient/inpatient exige fecha/sede/servicio. | V2-02A; fecha clínica/urgencia |
| A07 | admissions.read sin read_intake omite motivo/procedencia y demás intake; read_intake sin admissions.read no permite lectura. Datos ampliados del paciente sólo con read_demographics. | V2-02A/04; permisos |
| A08 | Datos V1 conservados sin evidencia ni fecha clínica inventadas; declaración verified V1 se distingue legacy_unsubstantiated; respuestas/esquemas V1 intactos. | V2-02A; compatibilidad |
| A09 | Huella V2 cubre perfil, razones de ausencia, verificación e intake; cambios dan conflicto. Claves separadas por versión; replay no duplica evidencia ni cambia autor/fecha. | V2-02B; idempotencia ampliada |
| A10 | API HTTP real y navegador: listas/borradores, urgencia incompleta, alta verificada documentada y restricción de intake; sin selector ni decisiones de prioridad/triage. | V2-05/06; recorrido ampliado |
| I01 | Misma clave/cuerpo: 201 → 200, mismo recurso/Location/vencimiento, false → true, correlaciones distintas. | V2-02; fiabilidad |
| I02 | Huella equivalente con espacios/NFC, orden de identificadores, defaults/null y UUID normalizados; cambia dato de negocio → 409. | V2-02; contrato |
| I03 | Cabecera ausente conserva comportamiento V1; en V2 falta → 422. Vacía, repetida, no UUID v4 → 422. | V2-02; compatibilidad |
| I04 | Mismo UUID de clave, actores/operaciones distintas: aislamiento; no revela registro ajeno. | V2-02; PAT-RNF-002 |
| I05 | Fallo de auditoría/creación revierte recurso/clave; mismo intento puede ejecutarse después. SQL directo no puede confirmar reserva pending sin recurso. | V2-02; PAT-RNF-003 |
| I06 | Dos conexiones reales con barrera y misma clave: un recurso, una creación, un replay; sin dos operaciones secuenciales. | V2-02; concurrencia |
| I07 | Mantener transacción competidora >5 s: 409 IN_PROGRESS/Retry-After; rollback y nuevo intento recuperan; lock_timeout sólo en reserva. | V2-02; concurrencia |
| I08 | Claves distintas, mismo paciente/tipo: dos episodios válidos incluso simultáneos. | V2-02; ADM-RF-003 |
| I09 | Replay tras search_id vencido; primera creación con acuse vencido → SEARCH_REQUIRED; renovar acuse compatible mantiene huella. V1 no lo consume. | V2-02; ADM-RF-001 |
| I10 | Revocar creación/verificación, suspender actor o apagar modo: 403/401 antes de replay; demografía revocada queda omitida. | V2-02; permisos |
| I11 | Justo antes/después de 24 h según reloj de base: replay / EXPIRED; reserva permanece; no renovar plazo ni crear otro recurso. | V2-02; retención |
| I12 | Perder respuesta HTTP después de commit; reiniciar API/PostgreSQL conservando datos; repetir recupera recurso/auditoría. | V2-02/06; persistencia |
| I13 | Replay audita acción propia, sin clave/cuerpo/huella; fallo de auditoría no devuelve éxito; errores y Cache-Control no-store. | V2-02; trazabilidad |
| F01 | Identidad apagada/inactivo rechazados; producción con bandera activa no arranca; alterar selector/cabecera de rol no concede permisos. | V2-03/06; seguridad |
| F02 | Buscar folio/nombre/TEST, AND, acentos/literales, página vacía/múltiple; selección explícita. | V2-04; PAT-RF-002/003 |
| F03 | Consulta-demo no recibe/renderiza/persiste demografía; 401/403 limpian vista; 404 no conserva paciente previo. | V2-04; PAT-RNF-002 |
| F04 | Cambio de actor/paciente/búsqueda con respuesta demorada: AbortController y generación descartan datos y errores anteriores. | V2-03/04/06; PAT-RNF-008 |
| F05 | URL directa, recarga, atrás/bfcache resuelven identidad/contexto; sin filtros/borradores en historial o storage. | V2-03/04/06; contexto |
| F06 | Alta provisional sin CURP, verificada sólo supervisor con dos identificadores/fuente; homónimo permitido; identificador reservado da conflicto recuperable. | V2-05; PAT-RF-001/003/004 |
| F07 | Desconocido sin nombre/nacimiento/documentos → paciente → emergency; etiquetas de pantalla nunca entran en JSON. | V2-05; PAT-RF-005, ADM-RF-004 |
| F08 | Cambio de datos o búsqueda expirada obliga revisión nueva; folio PAC visible al abrir; EPI distinto en resultado/consulta. | V2-05; ADM-RF-001/003 |
| F09 | Doble clic y corte de respuesta después de commit: UI conserva clave/cuerpo, reintento mismo recurso; no edición mientras incierto. | V2-05/06; fiabilidad |
| F10 | Recarga/cambio de actor/paciente durante alta incierta pierde memoria: consulta/reconciliación y aviso antes de otra alta. Desconocido sin folio requiere supervisor. | V2-06; límites |
| F11 | Auditoría sólo supervisor; una creación y replay separado; sin repetición de creación al reintentar. | V2-05/06; ADM-RNF-004 |
| F12 | Base caída, 422/409, errores con correlación; teclado, etiquetas, foco y anuncios; registrar tiempos navegador/configuración sin extrapolar SLA. | V2-06; experiencia |
| R01 | Regresión V1 completa, migración nueva/repetida/check, preparación idempotente y datos/configuración conservados. | V2-02/06; reproducibilidad |

Pruebas de red de respuesta perdida cortan **la respuesta después del commit**, no
sólo el request antes de llegar al servidor. Comprobar directamente conteos en base
y auditoría; no basta que UI muestre una sola fila. Para concurrencia, registrar
barrera y conexiones distintas. Vencimiento se prueba modificando fechas ficticias
del registro de prueba, sin cambiar el reloj del sistema ni esperar 24 horas.

## Revisiones humanas

- M2-01: ampliación de campos/reglas aprobada con «ok hazlo entonces» y concretada
  en revisión 2; [bocetos](bocetos-v2.html) y [guion](evidencia-v2-01.md) actualizados.
  No atribuir revisión visual ejecutada ni aceptación clínica; desarrollo autorizado.
- M2-02: pendiente de frontend/lecturas implementados y comandos reales comprobados.
- M2-03: pendiente de recorrido completo/pruebas y respuesta explícita del usuario.

Cada resultado futuro indicará caso, versión, comando, conteos, resultado y límites.
Esta matriz conserva la cobertura prevista; A01–A08 tienen evidencia de
ejecución V2-02A; I01–I13, A09 y R01 pasan en
[evidencia V2-02B](evidencia-v2-02b.md). Base navegador V2-03 comprobada: F01 y base F04/F05; escenarios completos
de búsqueda/ficha/altas se completan en V2-04–06. M2-01/02/03 no se consideran revisiones ejecutadas.

Validación vigente del backend: `backend/.venv/bin/python backend/scripts/verify_v2_02b.py`.

Validación de base frontend vigente: `backend/.venv/bin/python backend/scripts/verify_v2_03.py`.
