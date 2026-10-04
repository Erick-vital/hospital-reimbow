# Evidencia V3-02 — formularios administrativos simples

Fecha: 2026-10-03. Implementación autorizada expresamente: «implementa
V3-02 — simplificar formularios administrativos». Cierre técnico y revisión manual de formulario/prueba completada posteriormente
por el usuario. Las demás funcionalidades de M3-02 siguen pendientes.
[Plan](../plans/v3-expediente-basico.md), [contrato §2](contrato-v3.md#2-formularios-administrativos-directos-v3-02).

## Entrega

Paciente, perfil/contactos, descriptores del desconocido y episodio muestran
valores directamente. Las razones sólo aparecen con dato vacío; inicialmente
«No proporcionado», con desconocido y no aplica según campo. Escribir oculta
la razón, borrar la restaura; espacios son ausencia, NFC/extremos se normalizan.
Disponibilidad no concede verificación: provisional sigue siendo provisional.

Listas permiten añadir sin seleccionar conocido, hasta diez filas. Ausencia,
«Ninguno declarado» y filas informadas conservan sus cuerpos V2 distintos.
Quitar la última fila restaura ausencia; añadir retira la declaración vacía.
Filas de contactos, teléfonos, identificadores, domicilios y rango estimado
incompletas/inválidas bloquean revisión. Las filas conservan componentes propios
al retirar otra fila, para no intercambiar razones recordadas.

Cambio de identidad pide confirmar descarte cuando hay datos/razones; conserva
perfil, limpia identidad/descriptores/evidencia/búsqueda como corresponde.
Confirmación muestra valores y razones de ausencia, incluyendo listas y evidencia.
Ingreso ofrece hora actual sólo mediante acción explícita, muestra zona/offset,
valida fecha futura y exige ingreso/sede/servicio para consulta/hospitalización.
Cambiar sede limpia servicio y avisa. La procedencia sólo se copia por acción.

Sin cambios en backend, migraciones, API, permisos ni protocolo de intención:
el cuerpo/clave permanecen congelados ante resultados inciertos. Sin paquetes
instalados, despliegue ni cambios de configuración. Se conservaron los documentos
y evidencia previos de V3-01 y los originales de requerimientos.

## Comandos reproducibles y resultados

Desde raíz, usando dependencias y PostgreSQL/Chromium existentes:

```sh
npm --prefix frontend run typecheck
VITE_DEMO_IDENTITY=true npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Desde `backend/`:

```sh
.venv/bin/python -m pytest -q --junitxml=/tmp/v3-02-pytest.xml
```

- TypeScript y build correctos; build mantiene exclusión de identidad demo.
- 51 pruebas navegador/API pasan: 46 regresiones V2 adaptadas a captura directa
  y cinco escenarios adicionales agrupando A01–A07.
- 316 pruebas backend pasan sobre PostgreSQL; advertencia existente de Starlette
  sobre TestClient/httpx, sin instalar ni modificar dependencias por ella.
- [Resultado estructurado](evidencia/v3-02-resultados.json) conserva conteos,
  casos/duraciones y referencias ficticias; sin cuerpos ni credenciales.
- El runner usa `hospital_test`, inicia APIs/frontends propios y los cierra.
  Conserva fixtures ficticias; no borra pacientes, episodios ni volúmenes.

Primer recorrido: 45/46; W10 esperaba un input inexistente tras recarga, pero
la captura directa lo mantiene vacío. Se corrigió la aserción para comprobar
pérdida del borrador. Segunda ejecución: 51/51. La regresión backend y una
repetición del runner encontraron bloqueo del sandbox (PostgreSQL/EPERM);
se detuvo únicamente pytest propio y se ejecutaron fuera con permiso efectivo.

## Cobertura A01–A07 y límites

| Caso | Evidencia automatizada |
|---|---|
| A01–A02 | `forms-v3.spec.ts` captura directa, NFC, nacimiento, provisional, razón restaurada tras escribir/borrar/espacios/revisar/volver; W01 teléfono/sexo/listas persistidos. |
| A03 | W02 y R05 recuperación: desconocido con rango/procedencia o sin descriptores; identidad y nacimiento null, urgencia pendiente. Confirmar/cancelar descarte en ambos sentidos. |
| A04 | Lista sin declarar/ninguna explícita/añadir/quitar última; domicilio vacío y rango parcial bloquean; W01 contactos/teléfonos/domicilio, backend valida filas y estados. |
| A05 | W03 consulta con catálogos reales; nuevo caso cambia sede, limpia servicio y muestra aviso; campos exigidos en hospitalización, razones en urgencia y hora explícita. |
| A06 | W04 supervisor/evidencia e invalidación; prueba nueva verified sin permiso devuelve 403; regresión de permisos/proyección API. |
| A07 | 422 real inyectando entrada inválida hacia API real, 409 de identificador/clave, vencimiento real, respuesta perdida tras commit, doble clic, recarga/cambio de actor; replay y auditoría únicos. R02 envía HTTP simultáneo, backend conserva pruebas concurrentes. |

El usuario confirmó posteriormente su revisión manual: «acabo de revisar
manualmente la nueva version del fommulario y la prueba asi que ya puedes tachar
esa parte del plan». Se registra completada la revisión de formulario/prueba
V3-02; no se extiende a funcionalidades clínicas ni al recorrido final M3-02.
Teclado/foco y cabecera móvil cubiertos además por regresión R07. No hay
clínica implementada en esta etapa. La compatibilidad de razones históricas se
conserva en selectores/resumen y servidor V2; no se habilita edición de pacientes.
Riesgo de semilla administrativa permanece pendiente para V3-03, antes de clínica.
