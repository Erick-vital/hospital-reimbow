import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
const urls = JSON.parse(process.env.V2_E2E_URLS!)
const fixture = JSON.parse(process.env.V2_E2E_FIXTURES!)
const unique = () => 'Persona ficticia V205 ' + crypto.randomUUID()
async function known(page: Page, label: string, value: string) {
  await page.getByLabel(label, { exact: true }).fill(value)
}
async function start(page: Page, name = unique()) {
  await page.goto(urls.demo + '/patients/new')
  await known(page, 'Nombres', name)
  return name
}
async function search(page: Page) {
  await page.getByRole('button', { name: 'Buscar coincidencias del borrador' }).click()
  await expect(page.getByText(/coincidencias. Búsqueda válida/)).toBeVisible()
  await page.getByLabel('Revisé las coincidencias').check()
}
async function register(page: Page) {
  await page.getByRole('button', { name: 'Revisar registro', exact: true }).click()
  await page.getByRole('button', { name: 'Confirmar registro', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Paciente registrado', exact: true })).toBeVisible()
}
async function storage(page: Page) {
  expect(await page.evaluate(async () => [localStorage.length, sessionStorage.length, (await indexedDB.databases()).length, (await caches.keys()).length])).toEqual([0,0,0,0])
}

test('W01 · alta ampliada, listas, ausencias y apertura desde paciente nuevo', async ({ page }) => {
  const name = await start(page)
  await known(page, 'Nacionalidad', 'Ficticia V205')
  await page.getByLabel('Sexo registrado: razón de ausencia').selectOption('unknown')
  await page.getByRole('button', { name: 'Añadir teléfonos' }).click()
  await page.getByLabel('Número de teléfono').fill('5550002050')
  await page.getByRole('button', { name: 'Añadir teléfonos' }).click()
  await page.getByLabel('Número de teléfono').nth(1).fill('5550002051')
  await page.getByRole('button', { name: 'Quitar teléfonos 1' }).click()
  await page.getByRole('button', { name: 'Añadir domicilios' }).click()
  await page.getByLabel('Calle', { exact: true }).fill('Calle ficticia V205')
  await page.getByRole('button', { name: 'Añadir contactos de emergencia' }).click()
  await page.getByLabel('Nombre del contacto').fill('Contacto ficticio V205')
  await page.getByLabel('Relación del contacto: razón de ausencia').selectOption('not_applicable')
  await search(page)
  const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v2/patients'))
  await register(page)
  const body = await (await response).json()
  expect(body.given_names).toBe(name)
  expect(body.administrative_profile.phones.value).toEqual([{ kind: 'personal', number: '5550002051' }])
  expect(body.administrative_profile.registered_sex.state).toBe('unknown')
  await page.getByRole('link', { name: 'Consultar paciente y abrir episodio' }).click()
  await expect(page.getByText('Contacto ficticio V205', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Abrir nueva atención' }).click()
  await page.getByRole('button', { name: 'Revisar apertura' }).click()
  await expect(page.getByText('Confirmar paciente y atención')).toBeVisible()
  await page.getByRole('button', { name: 'Confirmar apertura' }).click()
  await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toBeVisible()
  await page.getByRole('link', { name: /Consultar episodio EPI/ }).click()
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(body.folio)
  await storage(page)
})

test('W02 · desconocido sin identidad inventada, rango y urgencia pendiente', async ({ page }) => {
  await page.goto(urls.demo + '/patients/new')
  await page.getByLabel('Tipo de identidad').selectOption('unknown')
  await page.getByLabel('Edad mínima estimada').fill('30')
  await page.getByLabel('Edad máxima estimada').fill('40')
  await known(page, 'Procedencia al registro', 'Procedencia ficticia V205')
  await search(page)
  const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v2/patients'))
  await register(page)
  const body = await (await response).json()
  expect(body.given_names).toBeNull(); expect(body.birth_date).toBeNull(); expect(body.identifiers).toEqual([])
  expect(body.unidentified_description.estimated_age.value).toEqual({ min_years: 30, max_years: 40 })
  await page.getByRole('link', { name: 'Consultar paciente y abrir episodio' }).click()
  await page.getByRole('link', { name: 'Abrir nueva atención' }).click()
  await expect(page.getByLabel('Procedencia del ingreso', { exact: true })).toHaveValue('')
  await page.getByRole('button', { name: 'Copiar procedencia del registro del paciente' }).click()
  await expect(page.getByLabel('Procedencia del ingreso', { exact: true })).toHaveValue('Procedencia ficticia V205')
  await page.getByRole('button', { name: 'Revisar apertura' }).click()
  await page.getByRole('button', { name: 'Confirmar apertura' }).click()
  await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toBeVisible()
  await storage(page)
})

test('W03 · paciente existente, catálogos y campos requeridos por tipo', async ({ page }) => {
  await page.goto(urls.demo + '/patients/' + fixture.second_patient_id + '/admissions/new')
  await page.getByLabel('Tipo de atención').selectOption('outpatient')
  await page.getByRole('button', { name: 'Revisar apertura' }).click()
  await expect(page.getByRole('alert')).toContainText('requieren fecha de ingreso')
  await known(page, 'Fecha clínica de ingreso', '2026-01-01T10:00')
  await expect(page.getByLabel('Sede', { exact: true }).locator('option')).not.toHaveCount(1)
  const site = await page.getByLabel('Sede', { exact: true }).locator('option').nth(1).getAttribute('value')
  await page.getByLabel('Sede', { exact: true }).selectOption(site!)
  await expect(page.getByLabel('Servicio', { exact: true }).locator('option')).not.toHaveCount(1)
  const service = await page.getByLabel('Servicio', { exact: true }).locator('option').nth(1).getAttribute('value')
  await page.getByLabel('Servicio', { exact: true }).selectOption(service!)
  const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v2/admissions'))
  await page.getByRole('button', { name: 'Revisar apertura' }).click()
  await expect(page.getByText('Confirmar paciente y atención')).toBeVisible()
  await page.getByRole('button', { name: 'Confirmar apertura' }).click()
  const body = await (await response).json()
  expect(body.type).toBe('outpatient'); expect(body.patient_id).toBe(fixture.second_patient_id)
  expect(body.intake.site_id.value).toBe(site); expect(body.intake.service_id.value).toBe(service)
  await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toBeVisible()
})

test('W04 · verificación supervisor, cambio de identidad invalida evidencia/búsqueda', async ({ page }) => {
  await page.goto(urls.demo + '/patients/new')
  await expect(page.getByLabel('Estado de identidad')).toHaveCount(0)
  await page.getByLabel('Actor de demostración', { exact: true }).selectOption('supervisor-demo')
  await known(page, 'Nombres', unique())
  await known(page, 'Fecha de nacimiento', '1990-01-01')
  await search(page)
  await page.getByLabel('Estado de identidad').selectOption('verified')
  for (const label of ['Nombre contrastado', 'Nacimiento contrastado']) {
    const fieldset = page.getByRole('group', { name: label, exact: true })
    await fieldset.getByLabel('Contraste', { exact: true }).selectOption('yes')
    await fieldset.getByLabel('Referencia descriptiva').fill('Documento ficticio V205')
  }
  await page.getByLabel('Nombres', { exact: true }).fill(unique())
  await expect(page.getByLabel('Estado de identidad')).toHaveValue('provisional')
  await expect(page.getByLabel('Revisé las coincidencias')).toHaveCount(0)
  await search(page)
  await page.getByLabel('Estado de identidad').selectOption('verified')
  for (const label of ['Nombre contrastado', 'Nacimiento contrastado']) {
    const fieldset = page.getByRole('group', { name: label, exact: true })
    await fieldset.getByLabel('Contraste', { exact: true }).selectOption('yes')
    await fieldset.getByLabel('Referencia descriptiva').fill('Documento ficticio V205')
  }
  const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v2/patients'))
  await register(page)
  const body = await (await response).json()
  expect(body.verification_quality).toBe('documented'); expect(body.verification.evidence).toHaveLength(2)
})

test('W05 · respuesta perdida tras commit, doble clic y replay conservan cuerpo/clave y un alta', async ({ page }) => {
  await start(page); await search(page)
  const sent: { key: string; body: string }[] = []
  let resource: string
  await page.route('**/api/v2/patients', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    sent.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! })
    const response = await route.fetch()
    if (sent.length === 1) { expect(response.status()).toBe(201); resource = (await response.json()).id; return route.abort('connectionfailed') }
    expect(response.status()).toBe(200); expect((await response.json()).id).toBe(resource)
    await route.fulfill({ response })
  })
  await page.getByRole('button', { name: 'Revisar registro', exact: true }).click()
  await page.getByRole('button', { name: 'Confirmar registro', exact: true }).evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click() })
  await expect(page.getByRole('button', { name: 'Reintentar el mismo intento' })).toBeVisible()
  await expect(page.getByLabel('Nombres', { exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Reintentar el mismo intento' }).click()
  await expect(page.getByRole('heading', { name: 'Paciente registrado' })).toBeVisible()
  expect(sent).toHaveLength(2); expect(sent[0]).toEqual(sent[1])
  const audit = await page.request.get(urls.demo + `/api/v1/audit?resource_id=${resource!}&action=patients.create`, { headers: { 'X-Dev-Actor': 'supervisor-demo' } })
  expect((await audit.json()).total).toBe(1)
  const replay = await page.request.get(urls.demo + `/api/v1/audit?resource_id=${resource!}&action=patients.replay`, { headers: { 'X-Dev-Actor': 'supervisor-demo' } })
  expect(replay.status()).toBe(200); expect((await replay.json()).total).toBe(1)
  await storage(page)
})

test('W06 · 409 identificador duplicado conserva borrador y permite seleccionar existente', async ({ page }) => {
  await start(page)
  await page.getByRole('button', { name: 'Añadir identificador', exact: true }).click()
  await page.getByLabel('Sistema', { exact: true }).selectOption('TEST')
  await page.getByLabel('Valor', { exact: true }).fill(fixture.test_identifier)
  await search(page)
  await expect(page.getByRole('link', { name: 'Seleccionar paciente existente ' + fixture.patient_folio })).toBeVisible()
  await page.getByRole('button', { name: 'Revisar registro' }).click()
  await page.getByRole('button', { name: 'Confirmar registro' }).click()
  await expect(page.getByRole('alert')).toContainText('IDENTIFIER_CONFLICT')
  await expect(page.getByLabel('Valor', { exact: true })).toBeEnabled()
  await expect(page.getByLabel('Valor', { exact: true })).toHaveValue(fixture.test_identifier)
  await page.getByRole('link', { name: 'Seleccionar paciente existente ' + fixture.patient_folio }).click()
  await expect(page.getByRole('heading', { name: 'Ficha de paciente' })).toBeVisible()
})

test('W07 · búsqueda expirada real en PostgreSQL conserva borrador y vuelve a buscar', async ({ page }) => {
  const name = await start(page)
  const response = page.waitForResponse(r => r.url().includes('/api/v2/patients?'))
  await search(page)
  const searchId = (await (await response).json()).search_id
  execFileSync(resolve('../backend/.venv/bin/python'), [resolve('scripts/backend.py'), '--expire-search', searchId], { cwd: resolve('..'), stdio: 'pipe' })
  await page.getByRole('button', { name: 'Revisar registro' }).click()
  await page.getByRole('button', { name: 'Confirmar registro' }).click()
  await expect(page.getByRole('alert')).toContainText('SEARCH_REQUIRED')
  await expect(page.getByLabel('Nombres', { exact: true })).toHaveValue(name)
  await search(page); await register(page)
})

test('W08 · rango inválido bloquea confirmación y conserva descriptor', async ({ page }) => {
  await page.goto(urls.demo + '/patients/new')
  await page.getByLabel('Tipo de identidad').selectOption('unknown')
  await page.getByLabel('Edad mínima estimada').fill('60'); await page.getByLabel('Edad máxima estimada').fill('40')
  await search(page)
  await page.getByRole('button', { name: 'Revisar registro' }).click()
  await expect(page.getByRole('alert')).toContainText('rango de edad estimada válido')
  await page.getByLabel('Edad máxima estimada').fill('70')
  await register(page)
})

test('W09 · auditoría autorizada filtra creación y consulta-demo recibe 403 directo', async ({ page }) => {
  await page.goto(urls.demo + '/audit')
  await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
  await page.getByLabel('Actor de demostración', { exact: true }).selectOption('supervisor-demo')
  await expect(page.locator('.audit-list')).toBeVisible()
  await page.getByLabel('Acción', { exact: true }).selectOption('patients.create')
  await page.getByLabel('UUID del recurso').fill(fixture.patient_id)
  await page.getByRole('button', { name: 'Consultar auditoría' }).click()
  await expect(page.getByRole('status')).toContainText('1 eventos')
  await expect(page.getByText('patients.create · success', { exact: true })).toBeVisible()
  for (const [path, body] of [['patients', { identity_status: 'provisional' }], ['admissions', { patient_id: fixture.patient_id, type: 'emergency' }]] as const) {
    const response = await page.request.post(urls.demo + '/api/v2/' + path, { headers: { 'X-Dev-Actor': 'consulta-demo', 'Idempotency-Key': crypto.randomUUID() }, data: body })
    expect(response.status()).toBe(403)
  }
  const response = await page.request.get(urls.demo + '/api/v1/audit', { headers: { 'X-Dev-Actor': 'consulta-demo' } }); expect(response.status()).toBe(403)
  await page.getByLabel('Actor de demostración', { exact: true }).selectOption('consulta-demo')
  await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
  await storage(page)
})

test('W10 · cambio de actor/recarga descarta borrador y URL resuelve contexto', async ({ page }) => {
  const name = await start(page)
  await page.getByLabel('Actor de demostración', { exact: true }).selectOption('supervisor-demo')
  await expect(page.getByText(name, { exact: false })).toHaveCount(0)
  await known(page, 'Nombres', name); await page.reload()
  await expect(page.getByLabel('Nombres', { exact: true })).toHaveValue('')
  await page.goto(urls.demo + '/patients/' + fixture.second_patient_id + '/admissions/new')
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText('Beta')
  await storage(page)
})

test('W11 · episodio con respuesta perdida, replay y otra atención explícita con clave nueva', async ({ page }) => {
  await page.goto(urls.demo + '/patients/' + fixture.second_patient_id + '/admissions/new')
  const requests: { key: string; body: string }[] = []
  const ids: string[] = []
  await page.route('**/api/v2/admissions', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    requests.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! })
    const response = await route.fetch(); ids.push((await response.json()).id)
    if (requests.length === 1) return route.abort('connectionfailed')
    expect(response.status()).toBe(requests.length === 2 ? 200 : 201)
    await route.fulfill({ response })
  })
  await page.getByRole('button', { name: 'Revisar apertura' }).click()
  await page.getByRole('button', { name: 'Confirmar apertura' }).evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click() })
  await page.getByRole('button', { name: 'Reintentar el mismo intento' }).click()
  await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toBeVisible()
  expect(requests[0]).toEqual(requests[1]); expect(ids[0]).toBe(ids[1])
  await page.getByRole('link', { name: 'Volver al paciente para abrir otra atención' }).click()
  await page.getByRole('link', { name: 'Abrir nueva atención' }).click()
  await page.getByRole('button', { name: 'Revisar apertura' }).click()
  await page.getByRole('button', { name: 'Confirmar apertura' }).click()
  await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toBeVisible()
  expect(requests).toHaveLength(3); expect(requests[2].key).not.toBe(requests[0].key); expect(ids[2]).not.toBe(ids[0])
  const audit = await page.request.get(urls.demo + `/api/v1/audit?resource_id=${ids[0]}&action=admissions.create`, { headers: { 'X-Dev-Actor': 'supervisor-demo' } })
  expect((await audit.json()).total).toBe(1)
  await page.goto(urls.demo + '/audit')
  await page.getByLabel('Actor de demostración', { exact: true }).selectOption('supervisor-demo')
  await page.getByLabel('Acción', { exact: true }).selectOption('admissions.replay')
  await page.getByLabel('UUID del recurso').fill(ids[0])
  await page.getByRole('button', { name: 'Consultar auditoría' }).click()
  await expect(page.getByText('admissions.replay · success', { exact: true })).toBeVisible()
})

test('W12 · conflicto de clave real bloquea otro envío y ofrece reconciliación', async ({ page }) => {
  await page.goto(urls.demo + '/patients/' + fixture.second_patient_id + '/admissions/new')
  let count = 0
  await page.route('**/api/v2/admissions', async route => {
    count++
    // La clave queda reservada en PostgreSQL con otro cuerpo, luego la petición
    // original recibe el conflicto real; no se simula JSON de éxito/error.
    const created = await route.fetch({ postData: JSON.stringify({ patient_id: fixture.patient_id, type: 'emergency' }) })
    expect(created.status()).toBe(201)
    const conflict = await route.fetch()
    expect(conflict.status()).toBe(409)
    await route.fulfill({ response: conflict })
  })
  await page.getByRole('button', { name: 'Revisar apertura' }).click()
  await page.getByRole('button', { name: 'Confirmar apertura' }).click()
  await expect(page.getByRole('alert')).toContainText('IDEMPOTENCY_CONFLICT')
  await expect(page.getByRole('link', { name: 'Consultar y reconciliar registros' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Reintentar el mismo intento' })).toHaveCount(0)
  await expect(page.getByLabel('Tipo de atención')).toBeDisabled()
  expect(count).toBe(1)
})

test('W13 · respuesta de alta tardía no vuelve al cambiar paciente', async ({ page }) => {
  await page.goto(urls.demo + '/patients/' + fixture.second_patient_id + '/admissions/new')
  let release!: () => void
  let captured!: () => void
  const gate = new Promise<void>(resolveDone => { release = resolveDone })
  const received = new Promise<void>(resolveDone => { captured = resolveDone })
  await page.route('**/api/v2/admissions', async route => {
    const response = await route.fetch(); expect(response.status()).toBe(201)
    captured(); await gate
    try { await route.fulfill({ response }) } catch { /* Contexto cancelado. */ }
  })
  await page.getByRole('button', { name: 'Revisar apertura' }).click()
  await page.getByRole('button', { name: 'Confirmar apertura' }).click()
  await received
  await page.evaluate(path => { history.pushState(null, '', path); dispatchEvent(new PopStateEvent('popstate')) }, '/patients/' + fixture.patient_id)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText('Alfa')
  release(); await page.unrouteAll({ behavior: 'wait' })
  await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toHaveCount(0)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText('Alfa')
})
