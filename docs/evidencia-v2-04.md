# Evidencia V2-04 — Búsqueda, ficha y episodios

Fecha: 2026-10-03. Validación técnica completada; **M2-02 preparada, sin revisión
humana ejecutada ni aprobación visual o clínica**. Desarrollo autorizado mediante
«continua con la fase: V2-04». No se implementaron formularios de V2-05.

## Implementación y decisiones

- Buscador con folio, nombre, CURP/TEST, combinación AND, desconocido explícito y
  tamaños de página; envío explícito, sin listado global ni filtros en la URL del navegador.
  Las peticiones API sí llevan sus filtros; logs de acceso permanecen apagados.
- Selección mediante enlace a UUID; folio y calidad identifican cada candidato.
  Coincidencia no confirma identidad ni fusiona pacientes. El filtro de desconocidos
  consulta únicamente `is_unidentified=true` de V2; no infiere desconocido de V1.
- Ficha administrativa con identidad, nacimiento, identificadores, sexo registrado,
  nacionalidad, teléfonos, domicilios y contactos múltiples. Razones unknown,
  not_provided y not_applicable se distinguen; known no implica verificado.
- Caracterización de desconocido separada: sexo aparente, rango de edad estimada,
  características, procedencia y traslado. Sin fabricar nombre ni nacimiento.
- Calidad documentada/pending/legacy_unsubstantiated visible sin mostrar documento,
  referencia, instantánea, actor o fecha de la evidencia de verificación.
  La respuesta autorizada de la API conserva su contrato y vive sólo en memoria.
- Cabecera del paciente permanece visible al desplazarse. Lista de episodios
  paginada y consulta muestran PAC/EPI separados, tipo/estado, registro e ingreso.
  La fecha clínica de ingreso no se sustituye con la de registro.
- Demografía sólo con patients.read_demographics; intake sólo con
  admissions.read_intake. Consulta-demo no recibe esos campos y muestra falta de
  permiso, sin tratarlos como desconocidos ni buscar otra proyección.
- Sede/servicio se muestran como UUID cuando están presentes. Los catálogos actuales
  exigen admissions.create; no se amplió ese permiso ni se añadieron llamadas para
  intentar resolverlos sin autorización. Nombres de catálogo quedan para su flujo
  de captura en V2-05 o una futura decisión explícita del contrato de lectura.
- `useResource` asocia datos/errores con ruta y número de consulta. Cambiar filtros
  o página oculta inmediatamente el resultado anterior; aborta la petición y
  descarta respuestas tardías. Repetir la misma búsqueda genera otra consulta real.
  Actor/ruta siguen usando generación y limpieza de V2-03. No hay cachés persistentes.

## Comandos y resultados comprobados

Desde la raíz, con PostgreSQL y dependencias/Chromium locales ya preparados en V2-03:

```sh
backend/.venv/bin/python backend/scripts/verify_v2_04.py
```

El verificador comprueba identidad apagada por defecto, preservación de filas previas
mediante hashes, .env sin cambios/permisos 0600 y lock conservado. Ejecuta typecheck,
build con bandera demo false/true, búsqueda de demo/credenciales en bundles,
navegador/API propios, capturas ficticias y regresión backend sobre PostgreSQL.
No instala dependencias, modifica el sistema, reinicia PostgreSQL ni borra datos.

Resultado final: **26 pruebas de navegador y 316 de backend pasan**, cero fallos,
errores u omisiones. Typecheck y ambos builds pasan. Advertencia existente:
Starlette depreca el transporte httpx de TestClient; no se cambiaron dependencias.
[Resultados con casos, duraciones, versiones y referencias ficticias](evidencia/v2-04-resultados.json).

Tras precisar el texto del filtro de desconocidos, se repitieron typecheck y build
false/true; ambos pasan. Las capturas del buscador usan el modo de identidad.
Comandos individuales:

```sh
npm --prefix frontend run typecheck
VITE_DEMO_IDENTITY=false npm --prefix frontend run build
VITE_DEMO_IDENTITY=true npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

El aislamiento inicial impidió el proceso/conexión de fixtures; la ejecución final
usó permisos efectivos para servicios locales. Durante desarrollo se corrigieron:
selectores ambiguos al aparecer el nombre también en la ficha; búsquedas previas
incompatibles en fixtures con TEST/desconocido; supuesto incorrecto de orden inverso
(en realidad la API ordena por created_at/id ascendente); selector accesible de `dt`.
Estas ejecuciones fallidas no se contaron como aceptación.

Las fixtures usan hospital_test/usuario test validado antes de escribir: pacientes
ficticios Alfa/Beta y otros candidatos (incluido Álvarez_%), uno desconocido, uno V1
con declaración verified sin evidencia, siete episodios de Alfa y actor sin permisos.
Se conservan; no hay escrituras de fixtures en hospital_dev. Ejecución repetible
puede acumular homónimos ficticios. API/Vite/preview/navegador propios cerrados;
PostgreSQL/volumen conservados, identidad backend por defecto apagada.

## Cobertura y límites

| Caso navegador | Evidencia principal |
|---|---|
| B01–B13, 16 pruebas | Regresión V2-03: proxy/identidad/build, rutas/recarga/atrás, 401/403/404, actores, cancelación, errores/foco y storage vacío. |
| R01 | F02: resultados comparados con JSON real, páginas sin solapamiento, selección por folio/UUID. |
| R02 | F02: TEST exacto, repetición real, vacío y 422 recuperable. |
| R03 | F04: búsqueda anterior demorada con respuesta real, descartada al enviar filtros nuevos. |
| R04 | F03/A08: colecciones/ausencias, calidad documentada y declaración V1, evidencia no renderizada. |
| R05 | A02 lectura: desconocido sin identidad inventada, rango separado, filtro y episodios vacíos. |
| R06 | Lista paginada, folios distintos, datos de ingreso, recarga y vuelta a la ficha. |
| R07 | F03/A07 lectura: consulta-demo sin demografía/intake en JSON/UI/storage tras cambiar actor. |
| R08 | Error de transporte en lista con identificación conservada, búsqueda recuperable. |
| R09 | F02: AND, mayúsculas/minúsculas, acento y `%_` literales. |
| R10 | F04: lista atrasada no contamina otro paciente; 404 de episodio sin identificación anterior. |

Respuestas positivas siempre reales; demoras/fallos de transporte se inyectan sobre
peticiones al proxy/API/PostgreSQL. No JSON de pacientes inventado en interceptores.
Sin traces/HAR/vídeos ni respuestas persistidas; evidencia JSON con conteos/IDs
ficticios y tiempos de casos completos, sin extrapolar un SLA o gran volumen.
`pageshow persisted` se comprueba con evento de ciclo, no restauración bfcache real.
A10, escritura/borradores, idempotencia de UI y auditoría visual siguen en V2-05/06.

Capturas inspeccionadas técnicamente (1440×960 y 390×844; página completa):
[búsqueda](evidencia/v2-04-busqueda.png), [ficha escritorio](evidencia/v2-04-ficha.png),
[ficha móvil](evidencia/v2-04-ficha-movil.png), [episodio móvil](evidencia/v2-04-episodio-movil.png).
Se observan etiquetas legibles, colecciones, folios y navegación sin recortes de texto.
La inspección del agente no sustituye la revisión humana M2-02.

## Guion M2-02 listo para revisión humana

Inicio desde raíz en dos terminales, usando exclusivamente la base de pruebas:

```sh
APP_ENV=test DEV_IDENTITY_ENABLED=true backend/.venv/bin/python -m uvicorn hospital.main:create_app --factory --app-dir backend/src --host 127.0.0.1 --port 8001 --no-access-log
```

```sh
V2_API_PORT=8001 VITE_DEMO_IDENTITY=true npm --prefix frontend run dev
```

URL: `http://127.0.0.1:5173/patients`. Los procesos de validación ya están cerrados;
estos comandos permiten iniciar una revisión nueva. Ctrl+C detiene API y frontend.
No cambiar .env ni activar identidad por defecto. Referencias de la última ejecución
en `browser.fixture_references` de los resultados enlazados arriba.

1. Como admision-demo, buscar «Persona ficticia navegador», tamaño 5, avanzar/volver.
   Buscar por `patient_folio` y seleccionar Alfa; repetir con Beta. Confirmar que el
   cambio de paciente es evidente y que una coincidencia requiere selección.
2. En Alfa revisar demografía, contactos y calidad documentada; seleccionar tamaño
   de atenciones 5, paginar y volver. Abrir `admission_folio`: comprobar PAC/EPI,
   ingreso clínico separado del registro y «Volver al paciente».
3. Cambiar a consulta-demo: identidad/folios siguen disponibles, la demografía y el
   motivo de ingreso no aparecen. Como inactivo-demo aparece acceso no disponible.
4. Volver a admision-demo. Consultar `/patients/{unknown_id}` y `/patients/{legacy_id}`:
   desconocido con rango estimado y sin nacimiento; declaración anterior sin evidencia.
   Comprobar recarga, teclado y lectura móvil. La recarga retorna al actor demo inicial.
5. Registrar respuesta explícita: aprobado/observaciones y pantallas afectadas.
   **Pendiente**: aún no hay respuesta humana ni aceptación funcional/clínica.
