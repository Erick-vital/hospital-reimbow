# V3-01 — contrato, bocetos y revisión M3-01

Fecha: 2026-10-03. **V3-01 cerrada por instrucción del usuario; inspección aplazada.**
Autorización literal: «comienza la primer etapa de plans/v3-expediente-basico.md».
Se comenzó esa etapa. No es respuesta a un diseño que todavía no se había presentado
ni autorización para iniciar V3-02–07.

Entregables: [contrato revisión 1](contrato-v3.md), [boceto navegable](bocetos-v3.html),
[matriz de aceptación/cobertura](validacion-v3.md),
[seguimiento del plan](../plans/v3-expediente-basico.md) y [estado](../ESTADO.md).
No se modificaron backend, frontend de aplicación, migraciones, dependencias o base.

## Revisión de antecedentes y discrepancias

ESTADO y plan V2 revisados antes de diseñar. Git estaba limpio, HEAD `cc86c8e`
(`feat(v2): registro, recuperación y entrega; plan de V3`). El plan V3 preparado
todavía decía que V2-06/commit faltaban: se corrigió ese siguiente paso con evidencia
del historial, sin convertir las revisiones funcionales V2 pendientes en aprobación.
No hay nuevas observaciones humanas sobre V2; se conserva esa limitación para V3.

Consultados propuesta técnica §§3/5/6/8.1/8.2 y requerimientos pertinentes de
Pacientes §5–10/13, Admisión §8–11, Médico §27–29, Enfermería §10–11 y Expediente
§4–7/12–15/23 y RF-001/002/003/004/008/010/019/020. Los originales se conservan.
La [matriz](validacion-v3.md) indica cobertura parcial y diferidos, especialmente
alergias referidas, una sola plantilla, mediciones sin escalas/alertas y tablero sin
asignaciones/camas. El diseño no acredita conformidad normativa.

Revisados esquemas y proyecciones V2, formularios `FormFields.tsx`, semilla de
identidad, autorización, errores e idempotencia. Dos hallazgos para implementación:

- La semilla actual calcula Admisión/Supervisor desde PERMISSIONS global. Agregar
  permisos clínicos sin cambiarla concedería clínica por herencia. Contrato §3
  exige listas explícitas administrativas antes de ampliar permisos; no se parcheó
  aún porque esta etapa sólo prepara diseño.
- El servicio `execute_create` enlaza reservas sólo a paciente/episodio. Las
  reservas clínicas deberán apuntar al registro o revisión exacta: replay de una
  edición no puede devolver la versión vigente que otro intento haya modificado.
  Contrato §8 define la extensión; sin implementación/transacción V3 comprobada.

Procesos revisados al inicio, sin asumir salud/ejecución de servicios por documentos.
No se levantaron API, Vite o PostgreSQL para esta fase ni se interrumpieron procesos
ajenos. No se repitieron suites V2: sus 316/46 resultados siguen siendo evidencia
anterior, no una ejecución ni una garantía de V3.

## Comprobación local del boceto

Se usaron Node 20.19.5, Playwright y Chromium existentes en `frontend/node_modules`
y `frontend/.cache/ms-playwright`, sin instalación. Página cargada por archivo local,
sin servidor/API. Escritorio 1280×900 y móvil 390×844, zona America/Monterrey.
Capturas sólo ficticias, sin traces/HAR/vídeos ni requests clínicos.

Primer arranque del navegador dentro del sandbox falló con `Operation not permitted`.
Se repitió fuera del sandbox con permiso del entorno. El primer recorrido detectó
ID duplicado entre motivo clínico y motivo de edición; se corrigió, junto con la
carga inicial del borrador para conservar texto al navegar. Rango estimado usa una
razón común; cabecera añade fecha de ingreso/sede/servicio autorizados.

Resultado final: **21 comprobaciones locales pasaron; cero errores de script**.
[Registro de resultados](evidencia/v3-01-resultados.json).
Comprueban visibilidad de campos directos, ocultar/restaurar ausencia, razón del
contacto en confirmación, ingreso pendiente/obligatorio según tipo, congelación y
reintento simulados, lista/filtro, PAC/EPI, conflicto simulado con texto conservado,
lectura de Enfermería sin edición, contexto O₂, denegación simulada de Consulta,
cambio de episodio, alergias compartidas en memoria, ancho móvil, etiquetas e IDs
DOM únicos. **No prueban permisos del servidor, idempotencia ni concurrencia real.**

Capturas guardadas e inspeccionadas técnicamente:

- [Formulario directo y confirmación, escritorio](evidencia/v3-01-formulario-desktop.png).
- [Contexto/cabecera, móvil](evidencia/v3-01-contexto-mobile.png).

El navegador propio se cerró con `finally`. Las capturas no son revisión humana.
Boceto con validación parcial para revisar presentación: anuncia registros simulados;
no serializa cuerpos V2/V3 ni ejecuta catálogo/versiones/auditoría reales. Historial
de alergias muestra un ejemplo y el editor un elemento; contrato admite hasta 20.
API/PostgreSQL y accesibilidad del producto deberán probarse en sus etapas.

Comandos efectivamente ejecutados desde raíz:

```sh
git status --short
git log -5 --oneline
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/ms-playwright" node /tmp/verify-v3-01.mjs
git diff --check
wc -l -w ESTADO.md
```

El recorrido automatizado fue un script temporal de esta sesión, sin añadir una
suite al producto. Para repetir la revisión, abrir `docs/bocetos-v3.html` en el
navegador y seguir el guion siguiente. Para comprobar carga y obtener otra captura
con herramientas ya instaladas, este comando es reproducible desde raíz:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/ms-playwright" node --input-type=module <<'JS'
import { chromium } from './frontend/node_modules/playwright/index.mjs';
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on('pageerror', error => { throw error; });
  await page.goto(new URL('./docs/bocetos-v3.html', 'file://' + process.cwd() + '/').href);
  await page.locator('#names').fill('Persona Nueva Ficticia');
  await page.screenshot({ path: '/tmp/v3-01-revision.png', fullPage: true });
} finally { await browser.close(); }
JS
```

Puede requerir ejecución fuera del sandbox por la restricción de Chromium ya
observada. No instala ni necesita reiniciar la base. Esta captura adicional no
reemplaza el recorrido ni sus resultados guardados.

Comprobación documental al preparar la entrega: seis documentos con enlaces locales existentes y
sin espacios finales; `git diff --check` sin errores. ESTADO: **58 líneas y 385
palabras**, dentro de ambos límites. Cambios limitados a plan/estado/documentos,
boceto y capturas/resultados V3-01; requerimientos originales intactos.

## Guion funcional M3-01 — inspección aplazada

Guion conservado como referencia; el usuario trasladó la inspección visual a la
funcionalidad final M3-02. No es una revisión previa obligatoria ni realizada.

Abrir el [boceto](bocetos-v3.html). No requiere iniciar servicios. Recargar vuelve
a los ejemplos iniciales; toda escritura es simulada. Revisar **primero formularios**:

1. Con admision-demo, escribir nombre/nacimiento sin selector previo de conocido.
   Dejar primer apellido vacío; elegir razón, escribirlo y borrarlo. Debe regresar
   la razón elegida. Añadir contacto con relación desconocida y teléfono no
   proporcionado; simular búsqueda y revisar que la confirmación conserva ambas.
2. Comparar lista sin declarar con «Ninguno declarado». Añadir teléfono/domicilio,
   quitar filas y revisar. Desconocido exige elección explícita, descarta identidad
   incompatible mediante confirmación y muestra descriptores opcionales/rango.
3. Con supervisor-demo, revisar verificación aparte (nombre más nacimiento/CURP
   y fuente ficticia), sin tratar el valor disponible como verificado.
4. En Ingreso, urgencias permite pendientes. Consulta/hospitalización exige fecha,
   sede y servicio; cambio de sede descarta servicio. Revisar resumen de paciente/tipo
   y simular respuesta perdida/reintento: datos congelados, mismo folio simulado.
5. Elegir medico-demo: revisar «Atenciones abiertas», filtros y los episodios 401,
   402 de Alfa y 403 de Beta. Abrir uno, regresar y abrir otro. Cabecera PAC/EPI
   cambia; episodio 402 no presenta las mediciones/notas del 401. Vista longitudinal
   agrupa por episodio y no conserva uno como seleccionado.
6. Revisar signos/unidades/fecha: presión muestra brazo/posición, temperatura sitio,
   SpO₂ contexto de oxígeno; vacío no es cero. Revisar tabla/ejemplo de evolución.
   No hay alertas ni clasificación diagnóstica. Decidir si el conjunto D04 basta.
7. Revisar cuatro estados de alergias (sin documento previo en la cabecera y tres
   declaraciones posibles), fuente/reacción/motivo/historial. Registrar declaración
   simulada y abrir otro episodio de Alfa: mismo resumen. Contrato D05 explica
   diferidos y conservación histórica; ejemplo no equivale a confirmación clínica.
8. Revisar nota inicial, plantilla/secciones, fecha, borrador parcial y nueva versión.
   Simular conflicto: texto permanece. Cambiar a enfermeria-demo y abrir la nota:
   lectura permitida propuesta, escritura deshabilitada. Cambiar a consulta-demo:
   contexto clínico no disponible. Revisar D03/D06 y móvil/teclado/foco.

Decisiones para responder: D01 captura directa/ausencias; D02 acceso demo global;
D03 lectura compartida de borradores y autoría; D04 mediciones/contextos;
D05 mínimo de alergias referidas; D06 plantilla/edición del borrador.
Todas se detallan al inicio del [contrato](contrato-v3.md).

## Respuesta del usuario y cierre

El 2026-10-03, después de presentar la inspección, el usuario indicó:

> mejor dejemos esta inspeccion visual para al final ya que tenga la funcionalidad yo te digo si me gusto o no aunque seguramente si me guste, da por cerrada esta etapa

Se registra **cierre explícito de V3-01 y aplazamiento de inspección visual** al
recorrido final con funcionalidad. Sustituye el requisito anterior de revisión
previa: M3-01 deja de bloquear los dependientes. No se registra inspección ejecutada,
agrado confirmado ni aprobación funcional individual de D01–D06; la expectativa
expresada por el usuario no sustituye su evaluación posterior.

D01–D06 se conservan como base de diseño revisable durante la entrega. Los
entregables técnicos de la etapa están preparados y comprobados como se detalla
arriba. Las pruebas de API/PostgreSQL y aceptación funcional final siguen pendientes
de sus etapas; conservar M3-02 con inspección de formularios y vistas implementadas.
Plan, contrato, matriz, propuesta técnica y ESTADO actualizados. Este cierre sólo
actualiza documentación, sin iniciar V3-02–07 ni alterar la aplicación.
Siguiente etapa: V3-02, simplificación de formularios administrativos.
Las revisiones V2 mantienen su estado separado.

Comprobación del cierre: enlaces locales/formato de los seis documentos válidos,
`git diff --check` sin errores; ESTADO **59 líneas y 403 palabras**, dentro de
ambos límites. Se conservan las 21 comprobaciones anteriores del boceto; no se
repitieron navegador/API/PostgreSQL por esta actualización documental.
