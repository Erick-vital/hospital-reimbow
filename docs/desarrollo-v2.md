# Desarrollo local V2 — base frontend

Comandos comprobados el 2026-10-03. V2-03 entrega estructura, identidad/permiso,
contextos y conexión; búsqueda/ficha ampliada y formularios siguen en V2-04/05.
[Estado](../ESTADO.md), [plan](../plans/v2-interfaz-admision.md),
[contrato](contrato-v2.md) y [evidencia](evidencia-v2-03.md).
Sólo datos ficticios. La identidad demo no autentica personas.

## Preparación

Desde la raíz del repositorio, con backend/entorno virtual ya preparados según
[desarrollo V1](desarrollo-v1.md). Node 20.19.5 y npm 10.8.2 comprobados.
Las dependencias directas se fijan en `frontend/package.json` y el árbol en su lock.

```sh
backend/.venv/bin/python backend/scripts/prepare_local.py
npm --prefix frontend ci
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

La preparación conserva `.env`, bases y volumen; no habilita identidad por defecto.
No guardar URLs de PostgreSQL ni credenciales en archivos/variables del frontend.
Vite sólo necesita el puerto local de la API (`V2_API_PORT`, 8001 por defecto).
No hay CORS ampliado: `/api` se reenvía por proxy a loopback conservando su prefijo.
Vite y preview escuchan en `127.0.0.1` y fallan si el puerto está ocupado.

## Arranque manual

Terminal 1, desde raíz, contra la base ficticia de pruebas usada por la evidencia:

```sh
APP_ENV=test DEV_IDENTITY_ENABLED=true backend/.venv/bin/python -m uvicorn hospital.main:create_app --factory --app-dir backend/src --host 127.0.0.1 --port 8001 --no-access-log
```

Terminal 2, desde raíz:

```sh
V2_API_PORT=8001 VITE_DEMO_IDENTITY=true npm --prefix frontend run dev
```

Abrir `http://127.0.0.1:5173/patients`. Detener ambos comandos con Ctrl+C.
Para usar `hospital_dev`, sustituir únicamente `APP_ENV=test` por `development`
en la API; los IDs de evidencia de `hospital_test` no existirán en esa base.
No hay cambios del `.env` para activar el demo: las banderas viven en cada proceso.

Actores: admision-demo, supervisor-demo, consulta-demo e inactivo-demo.
La consulta `/api/v1/identity/me` determina permisos actuales. Cambiar actor limpia
el contexto y cancela peticiones; seleccionar un actor no concede permisos propios.
Supervisor muestra entrada a Auditoría; consulta-demo no permite altas ni auditoría;
inactivo-demo produce 401. Registro, apertura de episodios y auditoría visual siguen pendientes de V2-05.

`/patients` permite filtros por folio/nombre/CURP/TEST (AND), desconocidos V2 y
paginación; no consulta un listado global. Los filtros viven sólo en memoria.
URLs `/patients/{UUID}` y `/admissions/{UUID}` resuelven ficha administrativa,
episodios paginados e ingreso autorizado; conservan PAC/EPI separados, recarga y
navegación atrás. La cabecera del paciente permanece visible al desplazarse.
Calidad documentada y declaración anterior sin evidencia se distinguen; el expediente
clínico no está implementado. Sede/servicio conocidos muestran UUID: sus catálogos
requieren admissions.create y no se solicitan para ampliar permisos de lectura.
Referencias ficticias y guion M2-02 en [evidencia V2-04](evidencia-v2-04.md).

Sin `VITE_DEMO_IDENTITY=true` el frontend no ofrece selector ni envía actor.
Sin `DEV_IDENTITY_ENABLED=true` el backend rechaza la consulta aunque el selector
esté visible. Cambiar variables exige reiniciar el proceso correspondiente.

## Build y preview

```sh
VITE_DEMO_IDENTITY=true npm --prefix frontend run build
V2_API_PORT=8001 npm --prefix frontend run preview
```

Incluso con la bandera true, el build excluye selector, actores y cabecera demo.
Preview tiene proxy explícito hacia API local; no activa identidad ficticia en el
frontend compilado. Su acceso protegido devuelve 401 sin autenticación real.
Esto no es un despliegue productivo; no hay proveedor de identidad implementado.
Los archivos de `dist/` no contienen configuración/credenciales de base.

## Navegador y validación

Instalación local de Chromium, sin paquetes del sistema ni `--with-deps`:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/ms-playwright" node frontend/node_modules/@playwright/test/cli.js install chromium
```

Validación del navegador, con build previo disponible:

```sh
VITE_DEMO_IDENTITY=true npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Validación completa/repetible de V2-04:

```sh
backend/.venv/bin/python backend/scripts/verify_v2_04.py
```

El verificador conserva el lock instalado y ejecuta typecheck/builds false/true; comprueba
artefactos sin demo/secretos, navegador y regresión backend, conserva hashes de
filas previas/configuración y guarda resultados. Requiere Chromium ya descargado.
Puede necesitar permiso efectivo para procesos locales, PostgreSQL y navegador.
La evidencia original V2-03 y su verificador se conservan; npm ci fue comprobado allí.

`test:e2e` valida `hospital_test` y usuario separado antes de crear fixtures ficticias.
Inicia dos APIs propias (demo activo/apagado) y cuatro frontends propios
(demo, frontend apagado, backend apagado y preview del build); cierra sus procesos.
`V2_API_PORT` opcional fija el puerto de su API propia; si está ocupado, falla.
No conecta a una API ajena ni escribe las fixtures en `hospital_dev`.
Los recursos ficticios nuevos se conservan; no se eliminan datos ni volúmenes.
Invocar directamente Playwright sin el runner se rechaza.

Todas las consultas positivas usan la API real. Demoras se aplican a respuestas
reales; las pruebas negativas inyectan fallos de transporte o actores realmente
sin acceso, sin fabricar JSON de pacientes. No hay traces, HAR, vídeos ni respuestas
persistidas. El informe conserva IDs ficticios, casos y conteos en `.cache/` ignorado.
`V2_CAPTURE_PREVIEW=true` conserva la opción de portada de V2-03.
`V2_CAPTURE_READ=true` captura búsqueda/ficha/episodio con datos ficticios;
el verificador V2-04 la usa como evidencia técnica, sin aprobación humana.

## Contexto y límites

Datos, actor, permisos y futuras intenciones viven sólo en memoria. Un cambio de
actor/ruta cancela AbortController, incrementa generación y desmonta el contenido;
un resultado/error anterior no se reutiliza. El ciclo pagehide/pageshow limpia y
revalida. 401/403 limpian datos y consultan identidad sin repetir la ruta denegada
en bucle; «Revalidar acceso» permite un nuevo intento explícito.
Errores usan textos propios y correlación validada, sin mostrar cuerpos del servidor.
Recarga pierde la selección de actor y vuelve al actor inicial de desarrollo.
No hay almacenamiento de datos en localStorage/sessionStorage/IndexedDB/Cache API
ni service worker. No se guardan borradores: los formularios se implementan en V2-05.
