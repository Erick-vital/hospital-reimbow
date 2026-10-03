# Evidencia V2-03 — Base frontend e identidad local

Fecha: 2026-10-03. Autorizada por «commitea los cambios y continua con la siguiente fase».
V2-02B guardada primero en commit `6e2c926`.
[Plan V2](../plans/v2-interfaz-admision.md), [contrato](contrato-v2.md),
[guía reproducible](desarrollo-v2.md) y [resultados](evidencia/v2-03-resultados.json).

Resultado: **16 pruebas de navegador y 316 backend pasan**, sin fallos ni omisiones.
Instalación reproducible, typecheck y builds false/true comprobados.

## Entregado y comprobado

React/TypeScript estricto, Vite, React Router declarativo y fetch nativo, con
package.json/lock fijados. Proxy `/api` sin reescribir hacia loopback; dev/preview
con host explícito y puerto estricto, `Cache-Control: no-store`, sin ampliar CORS.
CSS propio y layout adaptable; sin servicios, fuentes externas o kit visual.

Cliente HTTP, errores seguros/correlación, consulta de identidad y permisos,
selector ficticio sólo con bandera de desarrollo. Builds false/true excluyen
selector/actores/cabecera demo; no contienen URLs ni contraseñas de configuración.
No se crean contraseñas de usuarios ni se implementa autenticación real.

Cambio de actor/ruta invalida generación, cancela peticiones y desmonta contexto
para descartar datos locales. URL directa/recarga resuelve identidad/paciente/episodio
por API. 401/403 limpian datos y revalidan identidad, sin bucle de reintento de la ruta
denegada. 404 y fallos de transporte no arrastran identificación anterior.
Etiquetas, foco en encabezado, enlace para saltar al contenido y estados anunciados.

Sólo identificación y episodio básicos para comprobar resolución del contexto:
no buscador, lista/ficha administrativa completa, auditoría funcional ni formulario.
Los permisos protegen también esas rutas preparadas. Paciente/episodio se mantienen
separados; no se presenta la base como expediente clínico.

## Comandos

Desde la raíz, con dependencias y backend existentes:

```sh
npm --prefix frontend ci --cache /home/tao/repos/.cache/npm --prefer-offline --no-fund --no-audit
npm --prefix frontend run typecheck
VITE_DEMO_IDENTITY=true npm --prefix frontend run build
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/ms-playwright" node frontend/node_modules/@playwright/test/cli.js install chromium
backend/.venv/bin/python backend/scripts/verify_v2_03.py
```

Instalaciones locales autorizadas al iniciar esta fase: paquetes npm y Chromium
de Playwright dentro del proyecto/caché del repositorio. No cambios del sistema,
instalaciones globales, AWS ni despliegue. Registry/CDN y PostgreSQL/bind/navegador
requirieron ejecución fuera del sandbox; configuración existente conservada.
Node 20.19.5/npm 10.8.2. React/DOM/types 19.3.0, Vite 8.3.2/plugin React 6.1.1,
TypeScript 7.0.2, router 7.18.4, Playwright 1.63.0 y @types/node 20.19.5.
Chromium for Testing 153.0.8010.12, revisión Playwright 1243, en caché local ignorada.

Correcciones durante validación: condición del import dinámico del selector movida
al punto de compilación para evitar emitir su chunk inactivo. Regresión identificó
una prueba previa que suponía orden de eventos sin ORDER BY; se añadió orden explícito
por created_at/id en esa consulta de test. Sin cambio de negocio backend.
Primera corrida 15 pruebas de navegador; cobertura final añade 403 real durante consulta.

## Casos de navegador

| Casos | Comprobación |
|---|---|
| B01 | Proxy/browser consulta identidad real y permisos PostgreSQL; correlación/no-store; navegación de supervisor según permisos. |
| B02/B03 | Frontend apagado, backend apagado y preview compilado dan 401; build con true excluye selector/actores/cabecera. |
| B04 | URLs directas, recarga, paciente/episodio y retorno al paciente; PAC/EPI separados y foco correcto. |
| B05/B06 | Inactivo limpia contexto; actor inventado y cabecera de rol falsa no conceden acceso; consulta-demo recibe proyección básica y rutas restringidas. |
| B07/B08 | Respuesta 200 y error 404 reales retenidos en memoria hasta cambiar actor/paciente/ruta; AbortController/generación descartan resultado y error atrasados. |
| B09 | 404 tras paciente visible limpia datos; correlación servidor y sin correlación inventada para UUID inválido. |
| B10 | Atrás reconsulta identidad/contexto; handler pagehide/pageshow persisted limpia y revalida con evento de ciclo. No prueba restauración bfcache real. |
| B11 | Fallo de transporte inyectado, recuperación explícita, etiquetas/teclado/foco y ausencia de almacenamiento persistente. |
| B12/B13 | 401/403 de API real en consulta: actores inactivo/sin permisos, limpieza/revalidación y recuperación explícita. Sin fabricar cuerpos demográficos. |

Las cuatro variantes usan APIs propias con APP_ENV=test y hospital_test validada
antes de las escrituras de fixtures. Las respuestas positivas vienen de PostgreSQL,
sin mock de pacientes; demora mediante interceptación/forwarding de respuesta real.
Los fallos de transporte son inyección deliberada; no se miden como caída real de base.
Informe conserva conteos/IDs ficticios; traces/HAR/vídeos deshabilitados. No hay
localStorage/sessionStorage/IndexedDB/Cache API/service worker de la aplicación.

## Revisión visual técnica y límites

Capturas de portada, inspeccionadas por el agente: [escritorio](evidencia/v2-03-base-escritorio.png)
y [móvil](evidencia/v2-03-base-movil.png). Legibles sin recortes/desbordamiento;
no contienen datos de pacientes. No sustituyen aceptación humana M2-01/02/03.

V2-03 completa técnicamente; V2-04 es siguiente. No atribuir implementación del
buscador, ficha ampliada ni formularios/borradores/idempotencia en navegador.
F04/F05 comprueban la base de contextos y rutas; escenarios completos se mantienen
en V2-04–06. A10 y revisiones visuales/funcionales siguen pendientes.
API/Vite/preview/navegador temporales cerrados; PostgreSQL/volumen conservados.
Identidad backend sigue apagada por defecto; datos/configuración previos preservados.

Fuentes primarias consultadas: [Vite: host/proxy y consola](https://vite.dev/config/server-options.html),
[router declarativo](https://reactrouter.com/start/declarative/installation),
[Playwright: servidores de prueba](https://playwright.dev/docs/test-webserver).
Metadatos exactos comprobados con npm view; compatibilidad en ejecución acreditada
por lock/ci, typecheck/build y pruebas. No se afirma SLA, seguridad productiva ni
cumplimiento normativo.
