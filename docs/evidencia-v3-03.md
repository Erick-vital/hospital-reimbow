# Evidencia V3-03 — atenciones y contexto clínico

Fecha local: 2026-10-03. Autorización: «implementa V3-03».
**Cierre técnico; revisión funcional M3-02 pendiente.**
[Plan](../plans/v3-expediente-basico.md), [contrato](contrato-v3.md),
[guía](desarrollo-v3.md), [resultado estructurado](evidencia/v3-03-resultados.json).

## Entrega comprobada

API `/api/v3/clinical`: atenciones abiertas paginadas, filtros por tipo/sede/servicio,
catálogos activos, contexto por episodio, contexto longitudinal y lista por paciente.
Orden `created_at DESC, id DESC`; total/página/proyección del listado comparten
una sentencia PostgreSQL. Servicio exige sede; pareja incompatible devuelve 422,
catálogo inexistente/inactivo 404. Datos pendientes quedan incluidos sin filtro;
nombres históricos se conservan aunque el catálogo ya esté suspendido.

Proyección explícita: PAC/nombres/calidad de identidad y EPI/tipo/estado/fecha de
registro/ingreso/sede/servicio. Sin nacimiento, identificadores, perfil, evidencia,
procedencia ni motivo administrativo, incluso si el actor dispone de otros permisos.
Ingreso ausente no se sustituye por fecha de registro. Legacy conserva ausencia.

Médico y Enfermería demo reciben `patients.read`, `admissions.read` y sólo los
**tres permisos clínicos implementados**: contexto, atenciones y catálogos.
Admisión conserva siete permisos administrativos, Supervisor nueve y Consulta tres;
ninguno recibe clínica. Semilla repetida conserva UUID, suspensiones, permisos y
asignaciones revocadas; rechaza privilegios/roles ajenos. Permisos de signos,
alergias y notas se añadirán exclusivamente en sus etapas autorizadas.

Rutas y servicios comprueban autorización. Lecturas y eventos de éxito comparten
transacción; fallo de auditoría revierte el evento y evita devolver datos. Migración
0007 amplía CHECK de acciones/tipo de recurso y añade índices para lista/filtros.
Auditoría administrativa acepta esas acciones, con sólo IDs/metadatos mínimos.

Interfaz: atenciones abiertas, filtros/paginación, contexto con cabecera PAC/EPI
permanente, vista longitudinal con episodios separados y estados vacíos reales.
Cambio de actor/ruta, atrás y recarga cancelan solicitudes, limpian memoria y
revalidan identidad; respuestas tardías no repueblan otro contexto. No hay
formularios/borradores clínicos aún. No se crean secciones vacías de mediciones,
alergias o notas: su implementación corresponde a V3-04–06. Revocar lectura de
atenciones omite esa sección longitudinal; la vista anuncia acceso no disponible.

## Comandos y resultados

Desde raíz, dependencias y PostgreSQL/Chromium existentes:

```sh
APP_ENV=test backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
APP_ENV=test backend/.venv/bin/python backend/scripts/seed_identity.py
APP_ENV=development backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
APP_ENV=development backend/.venv/bin/python backend/scripts/seed_identity.py
npm --prefix frontend run typecheck
VITE_DEMO_IDENTITY=true npm --prefix frontend run build
V3_CAPTURE_CONTEXT=true npm --prefix frontend run test:e2e
```

Desde `backend/`:

```sh
.venv/bin/python -m pytest -q --junitxml=/tmp/v3-03-pytest.xml
```

- **339 backend pasan**: regresión V1/V2, 18 casos clínicos nuevos, dos actores
  adicionales y tres operaciones en las matrices existentes; PostgreSQL real. Upgrade repetido y
  `alembic check` en hospital_test coinciden con modelos/migración 0007.
- **57 navegador/API pasan**, incluidos seis casos clínicos nuevos y las 51
  pruebas previas. TypeScript y build correctos; actores demo excluidos del build.
- Semilla local: seis actores, cinco roles y doce permisos en ambas bases.
- Runner crea servicios propios, comprueba hospital_test y los cierra; conserva
  fixtures ficticias. No se ejecutaron instalaciones, despliegues, cambios de
  configuración ni eliminación de pacientes/episodios/volúmenes.
- El sandbox bloqueó PostgreSQL/runner; las ejecuciones afectadas se repitieron
  fuera con permiso efectivo. Advertencia previa de Starlette/httpx conservada.

Primer backend enfocado: 36/37; se corrigió una expectativa de offset original:
V2 conserva el instante UTC, comprobado como `2026-01-01T16:00:00Z`.
Primer navegador: 54/57; selección de sede cambió al locator del combobox,
validación de acceso móvil usa la región visible (el indicador desktop se oculta),
y fixtures mantienen siete episodios de Alfa para conservar aceptación R06 V2.
Repetición clínica 6/6 y recorrido final 57/57. Regresión backend final 339/339.

## Cobertura y límites

| Caso | Evidencia |
|---|---|
| C01 | Matriz de identidad y semilla repetida; listas administrativas explícitas, UUID/suspensiones/revocaciones preservados, exceso de permisos rechazado. |
| C02 | Alfa con dos episodios/Beta con uno en PostgreSQL; filtros/paginación/totales/pareja, contexto histórico, listas por paciente. Navegador compara con API real y cambia sede/servicio. |
| C03 | Episodio → longitudinal → otra atención → otro paciente → atrás; respuesta real retenida del contexto anterior; actor/recarga, memoria/storage vacíos, foco/teclado y cabecera móvil. |
| C04 | Seis actores en los seis endpoints, URL directa, básicos/contexto revocados, atenciones omitidas, 403/404, proyección sin campos restringidos; fallo de auditoría y denegación mínima. |

Capturas inspeccionadas técnicamente: [lista desktop](evidencia/v3-03-atenciones-desktop.png),
[contexto desktop](evidencia/v3-03-contexto-desktop.png),
[contexto móvil](evidencia/v3-03-contexto-mobile.png).
Se observan PAC/EPI y ausencias legibles, sin desbordamiento horizontal en móvil;
prueba de desplazamiento comprueba cabecera visible. No sustituyen aprobación humana.

C04 de lectura revocada de signos/alergias/notas permanece condicionado a V3-04–06:
no existen esas secciones ni permisos todavía. No se acreditan persistencia clínica,
concurrencia de ediciones, idempotencia clínica, migración clínica completa ni M3-02.
Los casos S/L/N/T siguen preparados; las garantías de reintento/concurrencia V2
sí pasan como regresión. Sin asignaciones, camas/equipos, autenticación real o firma.
