# Desarrollo local V3 — atenciones y contexto

V3-03 implementada el 2026-10-03; signos, alergias y notas aún pendientes.
[Evidencia/comandos comprobados](evidencia-v3-03.md), [plan](../plans/v3-expediente-basico.md).
Conservar el entorno y dependencias existentes de [V2](desarrollo-v2.md).

## Preparar y abrir

La migración vigente es 0007. Sobre bases locales ya configuradas:

```sh
APP_ENV=test backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
APP_ENV=test backend/.venv/bin/python backend/scripts/seed_identity.py
APP_ENV=development backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
APP_ENV=development backend/.venv/bin/python backend/scripts/seed_identity.py
```

No reactiva usuarios, permisos ni asignaciones revocados; ante configuración ajena
rechaza la semilla. No borra datos. Para instalar/preparar un entorno desde cero,
seguir las instrucciones V1/V2; estos comandos presuponen dependencias y PostgreSQL.

Terminal 1, raíz:

```sh
APP_ENV=test DEV_IDENTITY_ENABLED=true backend/.venv/bin/python -m uvicorn hospital.main:create_app --factory --app-dir backend/src --host 127.0.0.1 --port 8001 --no-access-log
```

Terminal 2, raíz:

```sh
V2_API_PORT=8001 VITE_DEMO_IDENTITY=true npm --prefix frontend run dev
```

Abrir `http://127.0.0.1:5173/clinical/attentions` y seleccionar **Médico · demo** o
**Enfermería · demo**. Admisión/Supervisor/Consulta no tienen acceso clínico.
Los actores clínicos no pueden buscar/crear pacientes, abrir ingresos, verificar
identidad ni consultar auditoría. El selector no autentica personas; sólo desarrollo.
Para consultar hospital_dev, sustituir APP_ENV=test por development en la API.

## Recorrido V3-03

1. Encontrar una atención abierta; filtrar tipo y, si hay permiso, sede/servicio.
2. Abrirla y comprobar nombre, PAC y EPI; ingreso pendiente conserva su razón.
3. Consultar vista longitudinal; PAC permanece y se indica «Sin episodio seleccionado».
4. Abrir otra atención o paciente y volver; comprobar cambio inequívoco de contexto.
5. Cambiar actor o recargar: identidad/datos se revalidan; recarga pierde actor demo
   y vuelve a Admisión. Seleccionar otra vez el actor clínico si corresponde.

UUID de paciente/episodio son las únicas referencias de recurso en rutas; filtros
viven en memoria. No hay camas, asignaciones ni secciones clínicas ficticias.
Las mediciones/alergias/notas sólo aparecerán cuando se implementen sus etapas.

## Verificación vigente

```sh
npm --prefix frontend run typecheck
VITE_DEMO_IDENTITY=true npm --prefix frontend run build
npm --prefix frontend run test:e2e
npm --prefix frontend run test:e2e -- clinical-v3.spec.ts
```

Desde backend: `.venv/bin/python -m pytest -q`.
`V3_CAPTURE_CONTEXT=true` en el runner guarda capturas ficticias en docs/evidencia.
Los servicios del runner se cierran automáticamente; los del arranque manual se
cierran con Ctrl+C. No ejecutar pruebas backend y navegador simultáneamente sobre
la base compartida. Los verificadores/evidencias de fases anteriores que fijan
0004/0006 son históricos; usar estos comandos para validar el árbol V3 vigente.
Revisión funcional final M3-02 pendiente.
