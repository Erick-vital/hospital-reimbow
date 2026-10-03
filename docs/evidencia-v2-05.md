# Evidencia V2-05 — Registro y apertura de episodios

Fecha: 2026-10-03. Implementación y validación técnica completadas; revisión
funcional humana pendiente. El usuario solicitó guardar los cambios actuales y
continuar V2-05. El commit previo es `45fb1e6` (V2-04). Sin despliegue ni instalaciones.

## Implementación y decisiones

- `/patients/new`: identidad conocida/parcial o completamente desconocida; campos
  con disponibilidad explícita, perfil y listas de hasta diez teléfonos/domicilios/
  contactos. Añadir/quitar sólo modifica el borrador. Descriptores del desconocido
  separados de identidad/nacimiento; rango sin valores numéricos inventados.
- Verificación sólo con patients.verify_identity: nombre más nacimiento/CURP,
  fuentes oficial/institucional y referencia descriptiva. El cliente no elige
  verificador/fecha. Cambiar identidad elimina evidencia y estado verified.
- Búsqueda dentro del formulario: primer identificador informado, nombre completo
  o unidentified si no hay identidad; acuse compatible emitido por API real, páginas
  de candidatos y declaración explícita de revisión. Una coincidencia se selecciona
  como paciente existente; no hay fusión. No transferir borradores/filtros sensibles
  en URL o history.state. La pantalla general enlaza un borrador vacío.
- Modificar identidad invalida búsqueda y descarta resultados atrasados; perfil
  compatible no invalida evidencia. Acuse válido 15 minutos; SEARCH_REQUIRED
  conserva borrador y exige volver a buscar. El servidor valida vigencia/compatibilidad.
- Confirmación de registro con identidad visible; servidor asigna UUID/PAC.
  Ficha permite abrir una atención para el paciente existente o recién creado.
- Ingreso: tipo, fecha/hora clínica local convertida a UTC, sedes y servicios de
  catálogo paginado. Cambiar sede borra servicio y cancela catálogo anterior.
  Urgencias admite pendientes; consulta/hospitalización requieren fecha/sede/servicio.
  Procedencia del desconocido sólo se copia mediante acción explícita.
- Confirmación paciente/PAC/tipo, resultado EPI y consulta; nueva atención requiere
  volver a la ficha y abrir explícitamente un formulario nuevo.
- Clave UUID v4 y cuerpo congelado juntos en memoria por intención. Bloqueo con ref
  antes del render protege doble clic; respuesta incierta bloquea edición y permite
  reintento idéntico. Sin reintento automático. 422/409 IDENTIFIER_CONFLICT confirman
  rechazo y permiten corregir; IDEMPOTENCY_CONFLICT/EXPIRED exigen reconciliar.
  Límite local conservador de 24 horas; la reserva/vigencia real la decide PostgreSQL.
  Salir/cambiar actor/paciente/recargar pierde el intento; aviso durante la incertidumbre.
- Auditoría autorizada con filtros UUID/acción y páginas; actor, fecha, recurso,
  correlación y creación/replay separados. No renderiza cuerpos demográficos.
  Corrección necesaria: Literal HTTP anterior omitía catalogs.read/patients.replay/
  admissions.replay, aunque eran eventos persistidos válidos. Ahora admite consulta
  sin filtro y filtros de replay, evitando validación de respuesta 500.

## Comando y resultados

Desde raíz, con dependencias/Chromium ya disponibles y PostgreSQL local:

```sh
backend/.venv/bin/python backend/scripts/verify_v2_05.py
```

**39 pruebas navegador/API y 316 backend pasan**, sin fallos, errores u omisiones.
Typecheck y builds demo false/true pasan; bundles excluyen selector/actor/cabecera
ficticios y credenciales. [Resultados, casos, versiones y referencias ficticias](evidencia/v2-05-resultados.json).
Comprobaciones de hash conservan filas previas de ambas bases, `.env` y lock;
identidad backend apagada por defecto. APIs/Vite/preview/Chromium propios cerrados;
PostgreSQL/volumen conservados. Fixtures y altas de navegador sólo en hospital_test.
Los nuevos recursos ficticios se conservan; no hay limpieza de pacientes/episodios.

El aislamiento bloqueó PostgreSQL/procesos: ejecución con permisos efectivos para
servicios locales. Se corrigieron durante la validación: siguiente foco de teclado
por nuevo enlace; etiquetas de select exactas; artefacto de scroll en capturas de
cabeceras sticky; prueba A02 que suponía desconocidos en primera página al acumular
fixtures. Ahora recorre páginas, sin borrar datos ni alterar orden de API.
Esas ejecuciones fallidas no cuentan como aceptación. Advertencia existente:
Starlette depreca httpx de TestClient; dependencias conservadas.

## Cobertura de navegador

| Caso | Comprobación |
|---|---|
| B01–B13 / R01–R10 | 26 regresiones: identidad, permisos, contexto, lectura, paginación, URL/recarga, storage vacío y teclado. |
| W01 | Perfil, listas añadir/quitar, ausencias, alta nueva → ficha → emergency → consulta con PAC/EPI. |
| W02 | Desconocido sin nombre/nacimiento/identificadores inventados; rango, copia explícita de procedencia y urgencia pendiente. |
| W03 | Paciente existente, obligatoriedad outpatient, sede/servicio y fecha con zona en JSON real; inpatient comparte controles/regla y mantiene A06 backend. |
| W04 | Supervisor verified documentado con dos fuentes; cambio de nombre limpia evidencia/búsqueda; admisión no ve verificación. |
| W05 | Doble clic y respuesta abortada después del commit paciente; replay 200, misma clave/cuerpo/UUID, una creación y un replay en auditoría. |
| W06 | Identificador reservado → 409 real; borrador editable/conservado y selección de paciente existente. |
| W07 | Acuse nuevo expirado en PostgreSQL mediante helper acotado a hospital_test; SEARCH_REQUIRED, búsqueda nueva y alta exitosa. |
| W08 | Rango inválido → 422 real, corrección sin descartar búsqueda compatible y alta. |
| W09 | Auditoría sin filtro y por UUID/acción; consulta-demo sin UI ni permiso directo de POST/auditoría. |
| W10 | Actor/recarga descartan borrador; URL de ingreso resuelve identificación desde API. |
| W11 | Episodio con respuesta perdida/doble clic/replay; otra atención explícita con clave/UUID nuevos; auditoría visual de replay. |
| W12 | Clave previamente reservada con otro cuerpo → conflicto real, edición bloqueada y enlace de reconciliación. |
| W13 | Alta confirmada en API con respuesta demorada; cambio de paciente descarta resultado tardío. |

Pruebas positivas usan API/PostgreSQL real; interceptores sólo retrasan/cortan
respuestas reales o provocan un conflicto real mediante peticiones de datos ficticios.
Sin JSON clínico fabricado, traces/HAR/vídeos ni cachés persistentes. Prueba W07
cambia sólo fechas de un acuse UUID recién creado (máximo dos minutos), respeta
restricción de expiración y no cambia el reloj del sistema. Concurrencia de conexiones
con barrera permanece probada en V2-02B; doble clic UI no se presenta como sustituto.

## Capturas y límites

Inspección técnica del agente en escritorio 1440×960 y móvil 390×844:
[registro](evidencia/v2-05-registro.png),
[desconocido móvil](evidencia/v2-05-desconocido-movil.png),
[ingreso móvil](evidencia/v2-05-ingreso-movil.png),
[auditoría](evidencia/v2-05-auditoria.png).
Formularios legibles, folio/identificación, confirmación y motivos de ausencia visibles;
no atribuir aprobación humana. Comandos de revisión en [guía](desarrollo-v2.md).

V2-06 pendiente: cierre de recuperación/base caída, concurrencia adicional de UI,
reconciliación tras pérdida completa de memoria, navegación/experiencia final y
M2-03. La comprobación pageshow es evento de ciclo, sin demostrar bfcache real.
M2-01 visual/M2-02/M2-03 no aprobadas por una persona. No autenticación real,
AWS, clínica completa, cumplimiento normativo ni aptitud productiva.
