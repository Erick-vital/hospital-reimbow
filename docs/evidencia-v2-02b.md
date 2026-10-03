# Evidencia V2-02B — Idempotencia y publicación local de altas

Fecha: 2026-10-03. Ejecución autorizada por «comitea los cambios actules y despues
continua con V2-02B». Cambios anteriores guardados primero en `a5a592d`.
Plan: [V2](../plans/v2-interfaz-admision.md); [contrato](contrato-v2.md).
Resultado: I01–I13, A09 y R01 comprobados sobre PostgreSQL y HTTP real.
[Resultados estructurados](evidencia/v2-02b-resultados.json).

## Implementación

Migración `0006`: tabla de reservas con UNIQUE por actor/operación versionada/UUID,
SHA-256 del modelo validado completo, fechas de base y FK RESTRICT a actor/paciente/
episodio. No almacena cuerpos ni respuestas. CHECK exige referencia del tipo correcto
y ventana de 24 horas; constraint trigger diferido impide confirmar una reserva
pending sin recurso. Nuevas acciones `patients.replay` y `admissions.replay`.

Servicio compartido dentro de la transacción de alta: reserva con INSERT ON CONFLICT,
creación/evidencia/intake/auditoría y completed se confirman juntos. El replay autoriza
primero y calcula una proyección vigente del recurso, con auditoría propia vacía y
correlación nueva. Revocar creación/verificación impide reproducir; revocar permisos
de campos omite demografía/intake. No exige permiso adicional de lectura ni renueva
el vencimiento, la verificación o sus fechas/autores.

POST `/api/v2/patients` y `/api/v2/admissions` publicados en la API local, con clave
obligatoria y Location V2. V1 conserva clave opcional y comportamiento sin clave.
UUID v4 canónico único validado; cabecera documentada en OpenAPI. Alta 201 y replay
200 con `Idempotency-Replayed` y `Idempotency-Expires-At`. Claves vencidas permanecen
reservadas; cuerpo diferente produce conflicto. Replay confirmado acepta acuse de
búsqueda vencido; una creación nueva conserva SEARCH_REQUIRED **422** de V1.

Reserva espera hasta 5 s y traduce sólo su lock_timeout a IN_PROGRESS 409 con
`Retry-After: 1`. Durante esa sentencia se desactiva el statement_timeout de 2 s
para que no anticipe la espera pactada. Ambos valores previos se restauran antes de
las reglas de negocio; otros errores conservan el tratamiento previo. No hay mutex
ni respuestas persistidas. Las respuestas API siguen con `Cache-Control: no-store`.

## Comandos y preservación

Entorno virtual y dependencias existentes; sin instalaciones nuevas ni despliegue.

```sh
backend/.venv/bin/python backend/scripts/prepare_local.py
backend/.venv/bin/python backend/scripts/verify_v2_02b.py
backend/.venv/bin/python backend/scripts/verify_v2_02b.py --migration-only
backend/.venv/bin/python -m pytest -q backend/tests -c backend/pyproject.toml --tb=short --junitxml=/tmp/reimbow-v2-02b-final.xml
```

El verificador completo prepara dos veces, compara hashes de todas las filas y
secuencias, conserva `.env`/modo 600 y la identidad apagada por defecto, migra desde
cero, comprueba transición 0005→0006 con datos V1/V2, repite upgrade/check, ejecuta
la suite y abre/cierra una API TCP temporal en loopback. `--migration-only` permite
repetir sólo la transición aislada y añadirla al informe existente.

La corrida inicial completa pasó 311 pruebas; la suite final pasa **316 pruebas**,
sin fallos ni omisiones, y añade comprobación
SQL de referencias completed y equivalencia de UTC/UUID/defaults de episodios.
Bases ficticias conservadas: `hospital_v2_02b_validation_a626a8f786364d0e8327b3aee3360c5b`
y `hospital_v2_02b_upgrade_85f71fd6af21469ba20bad65626936e0`.
La transición aislada comparó todas las filas previas (incluidos perfiles, evidencia,
intake, autoría, UUID, folios y fechas) y secuencias sin cambios. La preparación y
el reinicio preservaron datos/configuración de desarrollo y pruebas.
Pruebas con savepoints revierten sus datos; concurrencia y sondas TCP dejan nuevas
filas ficticias en `hospital_test`. No se borraron bases ni volúmenes.

## Evidencia por criterio

| Casos | Comprobación |
|---|---|
| I01/I02 | 201→200, mismo recurso/Location/vencimiento; NFC/espacios/defaults/null/identificadores ordenados, UUID canónico y fecha UTC equivalentes; cambio de negocio da conflicto. |
| I03/I04 | Ausencia opcional V1/obligatoria V2, vacía/repetida/no v4 rechazadas; aislamiento por actor, versión y operación. Altas y replay de pacientes/episodios V1/V2. |
| I05/I13 | Auditoría fallida revierte alta/clave y permite reintentar; auditoría de replay fallida no devuelve éxito ni agrega evento. SQL directo rechaza commit pending, referencias ausentes/dobles/de tipo incorrecto y FK inexistente. |
| I06/I08 | Barrera de dos hilos y pg_backend_pid distintos, tanto pacientes como episodios. Misma clave: un recurso/creación y un replay. Claves distintas: dos recursos y dos creaciones. |
| I07 | Competidor bloqueado devuelve IN_PROGRESS tras 5 s; rollback libera intención y reintento crea. SHOW comprueba restauración de ambos timeouts antes de insertar paciente. HTTP midió **5.011 s**, 409/Retry-After y recuperación con la misma clave. |
| I09 | Replay tras acuse vencido; nueva intención vencida rechazada; renovar acuse compatible mantiene huella. Un acuse vigente puede respaldar varias claves: V1 no lo consume. |
| I10 | Revocación de crear/verificar, suspensión y modo apagado; demografía/intake omitidos tras revocarlos; crear/replay funciona sin permiso de lectura adicional. |
| I11 | Ventana con reloj de base, antes/después del límite y reserva conservada; expiración 409 también por HTTP después del reinicio. |
| I12 | Proxy TCP recibe respuesta 201 completa del servidor y cierra sin entregarla al cliente. Se comprueba recurso/reserva completed en base antes del reintento 200. API reiniciada y PostgreSQL stop/up conservan recursos/reservas/auditoría; replay devuelve los mismos UUID/folios/fechas. |
| A09 | Huella incluye perfil, razones de ausencia, descriptores, verificación e intake; cambios producen conflicto. Replay no duplica evidencia ni fechas/autoría. |
| R01 | Regresión V1 y administrativa; migración desde cero/con datos/repetida/check; configuración y filas previas conservadas. |

## Límites y cierre

POST V2 operativo localmente; API temporal cerrada, PostgreSQL conservado en loopback.
No frontend, navegador, autenticación real, AWS ni afirmación clínica/productiva.
A10 y M2-02/03 siguen pendientes; M2-01 no acredita revisión visual ejecutada.
El verificador V2-02A conserva el guion histórico previo a la publicación; para
validar el backend vigente usar `verify_v2_02b.py`. Siguiente fase: V2-03.
