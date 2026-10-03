# V2-06 — Recuperación, validación y entrega

Fecha: 2026-10-03. **Validación técnica completada; revisión funcional pendiente.**
Plan: [V2-06](../plans/v2-interfaz-admision.md#v2-06--recuperación-validación-y-entrega).
Resultados y tiempos por caso: [JSON](evidencia/v2-06-resultados.json).
Se conserva la evidencia original [V1](validacion-v1.md), [02A](evidencia-v2-02a.md),
[02B](evidencia-v2-02b.md), [03](evidencia-v2-03.md), [04](evidencia-v2-04.md)
y [05](evidencia-v2-05.md), incluidas sus capturas.

## Comando reproducible y entorno

Desde raíz, con configuración/backend/dependencias/Chromium ya preparados según
[desarrollo V2](desarrollo-v2.md):

```sh
backend/.venv/bin/python backend/scripts/verify_v2_06.py
```

No instala paquetes. Repite dos veces `prepare_local.py`, aplica/comprueba migraciones
en ambas bases existentes y en una base nueva aislada conservada. Ejecuta typecheck,
builds con demo false/true, navegador/API reales y toda la regresión backend. Compara
hashes de filas anteriores de ambas bases, secuencias, configuración y lock.
Los resultados sólo se publican al pasar todas las comprobaciones.

PostgreSQL 18.6, revisión 0006; Node 20.19.5/npm 10.8.2, dependencias del lock vigente.
Chromium headless; escritorio y móvil 390 × 844. Fixtures ficticias sólo en
`hospital_test`, con usuario separado. Backend de desarrollo por defecto sin demo.
Configuración `.env` conservada con modo 0600; sin credenciales en builds/evidencia.
APIs/Vite/preview/navegador propios se cierran; no se detienen sesiones ajenas ni
se elimina el volumen. La base nueva de comprobación se conserva, no se borra.

## Resultado y cambios

46 casos de navegador/API y 316 pruebas backend PostgreSQL pasan, sin fallos,
errores u omisiones. Typecheck y ambos builds pasan. Preparación repetida y migración
desde cero/repetida/check pasan; filas previas, secuencias, lock y `.env` preservados.
La instalación original con `npm ci` está acreditada en V2-03; no se reinstaló ahora.

Los formularios muestran un aviso de recuperación antes de otra alta, incluso
después de recargar o cambiar actor, sin persistir borradores/claves. Dirige a la
búsqueda o a las atenciones del paciente. Para desconocido sin folio pide revisión
del supervisor. Explica que salir no cancela una operación ya recibida. La confirmación
recibe foco para revisar y enviar desde teclado.

| Caso de `recovery.spec.ts` | Evidencia comprobada |
|---|---|
| R01 | API propia conectada a puerto loopback sin PostgreSQL: 503 real, correlación UUID/no-store y mensaje sin SQL/configuración. UI conserva cuerpo/clave; reintento sobre API saludable crea. |
| R02 | Dos peticiones HTTP salen de una barrera común sin esperar respuesta: 201/200, mismo UUID y una creación auditada. La suite backend I06 comprueba barrera dentro del acceso SQL, conexiones independientes y conteos en PostgreSQL. |
| R03 | Commit 201 real, respuesta retenida hasta el timeout de 10 s; UI congela intento y replay 200 recupera UUID, cuerpo y clave sin otra creación. |
| R04 | Reserva nueva ficticia vencida en PostgreSQL respetando ventana de 24 h; retry recibe EXPIRED real, deshabilita otro envío y ofrece reconciliación. No cambia el reloj del sistema. |
| R05 | Desconocido creado con respuesta perdida; recarga pierde intención, muestra aviso y enlace de consulta/supervisor; no reenvía automáticamente. Storage vacío. |
| R06 | Cambio de actor tras commit con respuesta retenida: resultado anterior descartado, aviso disponible y ningún envío nuevo automático. |
| R07 | Teclado cambia tipo/revisa/confirma; foco en confirmación. Cabecera móvil permanece dentro del viewport al desplazar y muestra paciente correcto. |

Los otros 39 casos conservan búsqueda/candidatos, cambios de paciente/actor con
respuestas atrasadas, permisos, demografía/intake restringidos, búsqueda expirada,
desconocido, 422/409, doble clic, pérdida de respuesta de paciente/episodio y auditoría.
Backend vuelve a probar permisos revocados, concurrencia, rollback, conservación
de evidencia y V1. Los helpers de vencimiento sólo afectan UUID nuevos en hospital_test;
las filas previas se comparan al terminar.

## Límites

La base inaccesible se prueba mediante conexión PostgreSQL real fallida en API
propia. El contenedor compartido permanece disponible; caída/reinicio físico y
recuperación persistente están acreditados en V2-02B, sin repetir la interrupción.
La concurrencia HTTP no afirma por sí sola colisión dentro de SQL: esa condición
la comprueba I06 con barrera/conexiones separadas durante esta misma regresión.

Los tiempos del JSON son duración de casos automatizados, incluidas esperas e
interacción; no latencia de cada endpoint ni rendimiento bajo carga/SLA. Timeout
del cliente: 10 s; reserva de idempotencia: espera máxima 5 s, retención 24 h.
`pageshow persisted` se comprueba con evento; sin afirmar restauración bfcache real.
Intenciones distintas pueden crear atenciones distintas. Tras perder la intención
no puede recuperarse su clave desde este frontend; requiere consulta/revisión.

Sin autenticación real, firma clínica, aceptación clínica ni preparación productiva.
Las pruebas/capturas técnicas no sustituyen M2-01/02/03.

## Revisión funcional M2-03 preparada

Estado: **pendiente de respuesta explícita del usuario**. No se solicitó aprobar
automáticamente por tener pruebas verdes. Arranque en dos terminales desde raíz:

```sh
APP_ENV=test DEV_IDENTITY_ENABLED=true backend/.venv/bin/python -m uvicorn hospital.main:create_app --factory --app-dir backend/src --host 127.0.0.1 --port 8001 --no-access-log
```

```sh
V2_API_PORT=8001 VITE_DEMO_IDENTITY=true npm --prefix frontend run dev
```

URL: `http://127.0.0.1:5173/patients`. Si esos puertos están ocupados por tu sesión,
usa esa sesión o elige otro puerto API y pásalo en ambos comandos; para frontend
agrega `-- --port 5174`. No detener servicios ajenos. Datos ficticios de referencia:
UUID/folios en `browser.fixture_references` del JSON. También puede buscarse por
nombre «Persona ficticia Alfa 204» y seleccionar un candidato explícitamente.

1. Como admision-demo, buscar/seleccionar un paciente existente; revisar PAC y
   episodios. Abrir atención de urgencias con pendientes y consultar su EPI.
2. Registrar una persona ficticia nueva con nombre, contactos/ausencias; revisar
   coincidencias, confirmar y abrir episodio. Revisar confirmación por teclado.
3. Registrar desconocido con rango estimado/descriptores opcionales; verificar que
   no se inventan nombre/nacimiento/CURP y que permite abrir urgencias.
4. Revisar avisos antes de otra alta, consulta tras recargar y advertencia de
   supervisor para desconocido sin folio. El reintento por respuesta perdida y la
   concurrencia se reproducen con el verificador; no apagar PostgreSQL compartido.
5. Como consulta-demo, comprobar lectura limitada sin altas, intake ni auditoría.
   Como supervisor-demo, revisar verificación documentada y auditoría de creación/replay.
6. Repetir cambio de paciente/actor y recorrido móvil; informar si se pierde el
   contexto o si los mensajes/confirmaciones resultan confusos.

Registrar respuesta, observaciones y acciones en este documento y plan/ESTADO.
M2-01 visual y M2-02 siguen pendientes; aprobación del desarrollo no acredita estas
revisiones. V3 tiene [plan preparado](../plans/v3-expediente-basico.md), sin iniciar
su implementación ni simplificar formularios administrativos dentro de V2-06.
