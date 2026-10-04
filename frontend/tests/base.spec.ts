import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { readFileSync, readdirSync } from 'node:fs'

const urls: Record<string, string> = JSON.parse(process.env.V2_E2E_URLS!)
const fixture: { patient_id: string; second_patient_id: string; patient_folio: string; admission_id: string; admission_folio: string; denied_actor: string } = JSON.parse(process.env.V2_E2E_FIXTURES!)
const patientName = 'Persona ficticia navegador Alfa'
const secondName = 'Persona ficticia navegador Beta'
const actor = (page: Page) => page.getByLabel('Actor de demostración', { exact: true })

async function selectActor(page: Page, value: string) {
  await actor(page).selectOption(value)
  await expect(page.getByText('Acceso comprobado', { exact: true })).toBeVisible()
}
async function spaNavigate(page: Page, path: string) {
  await page.evaluate(path => { history.pushState(null, '', path); window.dispatchEvent(new PopStateEvent('popstate')) }, path)
}
async function noPersistentData(page: Page) {
  const storage = await page.evaluate(async () => ({
    local: localStorage.length, session: sessionStorage.length, databases: (await indexedDB.databases()).length,
    caches: (await caches.keys()).length, workers: (await navigator.serviceWorker.getRegistrations()).length,
  }))
  expect(storage).toEqual({ local: 0, session: 0, databases: 0, caches: 0, workers: 0 })
}

test('B01 · navegador y proxy consultan identidad real PostgreSQL', async ({ page }) => {
  const response = page.waitForResponse('**/api/v1/identity/me')
  await page.goto(urls.demo + '/patients')
  const identity = await response
  expect(identity.status()).toBe(200)
  expect(identity.headers()['cache-control']).toBe('no-store')
  expect(identity.headers()['x-request-id']).toMatch(/^[0-9a-f-]{36}$/)
  expect((await identity.json()).permissions).toContain('patients.create')
  await expect(page.getByRole('heading', { name: 'Pacientes', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Auditoría', exact: true })).toHaveCount(0)
  await selectActor(page, 'supervisor-demo')
  await expect(page.getByRole('link', { name: 'Auditoría', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Auditoría', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Auditoría', exact: true })).toBeVisible()
  await noPersistentData(page)
})

for (const mode of ['frontend-off', 'backend-off', 'build']) {
  test(`B02 · ${mode} rechaza acceso y protege el contexto`, async ({ page }) => {
    const response = page.waitForResponse('**/api/v1/identity/me')
    await page.goto(urls[mode] + '/patients/' + fixture.patient_id)
    expect((await response).status()).toBe(401)
    await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
    await expect(page.getByText(patientName, { exact: true })).toHaveCount(0)
    await expect(actor(page)).toHaveCount(mode === 'backend-off' ? 1 : 0)
    await expect(page.getByText('Referencia de la solicitud:', { exact: false })).toBeVisible()
    await noPersistentData(page)
  })
}

test('B03 · build incluso con bandera true excluye selector y actores', async () => {
  const scripts = readdirSync('dist/assets').filter(name => name.endsWith('.js'))
  expect(scripts.some(name => name.includes('DemoSelector'))).toBe(false)
  for (const file of scripts) {
    const source = readFileSync('dist/assets/' + file, 'utf8')
    for (const forbidden of ['Actor de demostración', 'admision-demo', 'supervisor-demo', 'medico-demo', 'enfermeria-demo', 'X-Dev-Actor']) expect(source).not.toContain(forbidden)
  }
})

test('B04 · URL directa y recarga resuelven paciente y episodio', async ({ page }) => {
  await page.goto(urls.demo + '/patients/' + fixture.patient_id)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
  await expect(page.getByText(fixture.patient_folio, { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Ficha de paciente' })).toBeFocused()
  const identity = page.waitForResponse('**/api/v1/identity/me')
  await page.reload()
  expect((await identity).status()).toBe(200)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
  await page.goto(urls.demo + '/admissions/' + fixture.admission_id)
  await expect(page.getByRole('heading', { name: fixture.admission_folio })).toBeVisible()
  await expect(page.getByText(fixture.patient_folio, { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Volver al paciente' }).click()
  await expect(page).toHaveURL(urls.demo + '/patients/' + fixture.patient_id)
  await noPersistentData(page)
})

test('B05 · actor inactivo limpia datos y permiso no se obtiene alterando selector', async ({ page }) => {
  await page.goto(urls.demo + '/patients/' + fixture.patient_id)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
  await actor(page).selectOption('inactivo-demo')
  await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
  await expect(page.getByText(patientName, { exact: true })).toHaveCount(0)
  await actor(page).evaluate((select: HTMLSelectElement) => {
    const option = document.createElement('option')
    option.value = 'administrador-inventado'; option.text = 'Administrador'
    select.add(option); select.value = option.value; select.dispatchEvent(new Event('change', { bubbles: true }))
  })
  await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
  await expect(page.getByText(fixture.patient_folio, { exact: true })).toHaveCount(0)
  await noPersistentData(page)
})

test('B06 · consulta-demo, cabecera de rol falsa y permisos de rutas', async ({ page }) => {
  await page.goto(urls.demo + '/patients')
  await selectActor(page, 'consulta-demo')
  await spaNavigate(page, '/patients/new')
  await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
  const denied = await page.evaluate(async patientId => {
    const response = await fetch('/api/v2/admissions', { method: 'POST', cache: 'no-store', headers: {
      'Content-Type': 'application/json', 'X-Dev-Actor': 'consulta-demo', 'X-Role': 'supervisor-demo', 'Idempotency-Key': crypto.randomUUID(),
    }, body: JSON.stringify({ patient_id: patientId, type: 'emergency' }) })
    return { status: response.status, body: await response.json() }
  }, fixture.patient_id)
  expect(denied.status).toBe(403)
  expect(denied.body.error.code).toBe('PERMISSION_DENIED')
  const basicResponse = page.waitForResponse('**/api/v2/patients/' + fixture.patient_id)
  await spaNavigate(page, '/patients/' + fixture.patient_id)
  const basic = await basicResponse
  expect(await basic.json()).not.toHaveProperty('administrative_profile')
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
  await spaNavigate(page, '/audit')
  await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
  await noPersistentData(page)
})

for (const change of ['actor', 'patient']) {
  test(`B07 · respuesta real demorada se descarta al cambiar ${change}`, async ({ page }) => {
    let release!: () => void
    let captured!: () => void
    const delayed = new Promise<void>(resolve => { release = resolve })
    const received = new Promise<void>(resolve => { captured = resolve })
    await page.route('**/api/v2/patients/' + fixture.patient_id, async route => {
      const response = await route.fetch() // Respuesta real del proxy/API/PostgreSQL.
      captured()
      await delayed
      try { await route.fulfill({ response }) } catch { /* Solicitud cancelada al cambiar contexto. */ }
    })
    await page.goto(urls.demo + '/patients/' + fixture.patient_id)
    await received
    await expect(page.getByRole('status').filter({ hasText: 'Resolviendo el paciente' })).toBeVisible()
    if (change === 'actor') {
      await actor(page).selectOption('inactivo-demo')
      await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
    } else {
      await spaNavigate(page, '/patients/' + fixture.second_patient_id)
      await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(secondName)
    }
    release()
    await page.unrouteAll({ behavior: 'wait' })
    await expect(page.getByText(patientName, { exact: true })).toHaveCount(0)
    await expect(page.getByText(fixture.patient_folio, { exact: true })).toHaveCount(0)
    await noPersistentData(page)
  })
}

test('B08 · error real tardío no reemplaza el contexto nuevo', async ({ page }) => {
  const missing = 'ffffffff-ffff-4fff-afff-ffffffffffff'
  let release!: () => void
  let captured!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  const received = new Promise<void>(resolve => { captured = resolve })
  await page.route('**/api/v2/patients/' + missing, async route => {
    const response = await route.fetch()
    expect(response.status()).toBe(404)
    captured()
    await gate
    try { await route.fulfill({ response }) } catch { /* Contexto anterior cancelado. */ }
  })
  await page.goto(urls.demo + '/patients/' + missing)
  await received
  await spaNavigate(page, '/patients/' + fixture.patient_id)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
  release()
  await page.unrouteAll({ behavior: 'wait' })
  await expect(page.getByRole('heading', { name: 'Registro no encontrado' })).toHaveCount(0)
})

test('B09 · 404 limpia paciente previo, errores llevan correlación', async ({ page }) => {
  await page.goto(urls.demo + '/patients/' + fixture.patient_id)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
  await spaNavigate(page, '/patients/ffffffff-ffff-4fff-afff-ffffffffffff')
  await expect(page.getByRole('heading', { name: 'Registro no encontrado' })).toBeVisible()
  await expect(page.getByText('Referencia de la solicitud:', { exact: false })).toBeVisible()
  await expect(page.getByText(patientName, { exact: true })).toHaveCount(0)
  await spaNavigate(page, '/patients/no-es-uuid')
  await expect(page.getByRole('heading', { name: 'Registro no encontrado' })).toBeVisible()
  await expect(page.getByText('Referencia de la solicitud:', { exact: false })).toHaveCount(0)
})

test('B10 · navegación atrás y ciclo pageshow revalidan identidad', async ({ page }) => {
  await page.goto(urls.demo + '/patients/' + fixture.patient_id)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
  await spaNavigate(page, '/patients/' + fixture.second_patient_id)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(secondName)
  const identity = page.waitForResponse('**/api/v1/identity/me')
  await page.goBack()
  expect((await identity).status()).toBe(200)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
  await expect(page.getByText(secondName, { exact: true })).toHaveCount(0)
  const refreshed = page.waitForResponse('**/api/v1/identity/me')
  await page.evaluate(() => {
    dispatchEvent(new PageTransitionEvent('pagehide', { persisted: true }))
    dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))
  })
  expect((await refreshed).status()).toBe(200)
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
})

test('B11 · fallo de transporte recuperable, etiquetas, teclado y foco', async ({ page }) => {
  await page.route('**/api/v1/identity/me', route => route.abort('connectionrefused'))
  await page.goto(urls.demo + '/patients')
  await expect(page.getByText('No fue posible conectar con el servidor. Intenta nuevamente.')).toBeVisible()
  await expect(page.getByText('Referencia de la solicitud:', { exact: false })).toHaveCount(0)
  await page.unrouteAll()
  await page.getByRole('button', { name: 'Revalidar acceso' }).click()
  await expect(page.getByRole('heading', { name: 'Pacientes', exact: true })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Registrar paciente nuevo' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('Tipo de búsqueda')).toBeFocused()
  await page.getByRole('button', { name: 'Revalidar acceso' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Pacientes', exact: true })).toBeFocused()
  expect(await actor(page).getAttribute('id')).toBe('demo-actor')
  await noPersistentData(page)
})

test('B12 · 401 real en consulta limpia contexto y revalida identidad', async ({ page }) => {
  await page.goto(urls.demo + '/patients')
  await selectActor(page, 'supervisor-demo')
  let captured!: () => void
  const forwarded = new Promise<void>(resolve => { captured = resolve })
  await page.route('**/api/v2/patients/' + fixture.patient_id, async route => {
    // Inyección de fallo: misma API real, identidad suspendida en esta petición.
    const response = await route.fetch({ headers: { ...route.request().headers(), 'x-dev-actor': 'inactivo-demo' } })
    expect(response.status()).toBe(401)
    await route.fulfill({ response })
    captured()
  })
  await spaNavigate(page, '/patients/' + fixture.patient_id)
  await forwarded
  await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
  await expect(page.getByText(patientName, { exact: true })).toHaveCount(0)
  await page.unrouteAll()
  await page.getByRole('button', { name: 'Revalidar acceso' }).click()
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
})


test('B13 · 403 real en consulta limpia contexto y revalida permisos', async ({ page }) => {
  await page.goto(urls.demo + '/patients')
  const revalidated = page.waitForResponse(response => response.url().endsWith('/api/v1/identity/me') && response.request().headers()['x-dev-actor'] === 'supervisor-demo')
  await selectActor(page, 'supervisor-demo')
  await revalidated
  await page.route('**/api/v2/patients/' + fixture.patient_id, async route => {
    const response = await route.fetch({ headers: { ...route.request().headers(), 'x-dev-actor': fixture.denied_actor } })
    expect(response.status()).toBe(403)
    await route.fulfill({ response })
  })
  const nextIdentity = page.waitForResponse('**/api/v1/identity/me')
  await spaNavigate(page, '/patients/' + fixture.patient_id)
  await nextIdentity
  await expect(page.getByRole('heading', { name: 'Acceso no disponible' })).toBeVisible()
  await expect(page.getByText(patientName, { exact: true })).toHaveCount(0)
  await expect(page.getByText('El actor actual no tiene permiso para esta acción.')).toBeVisible()
  await page.unrouteAll()
  await page.getByRole('button', { name: 'Revalidar acceso' }).click()
  await expect(page.getByRole('region', { name: 'Paciente del contexto actual' })).toContainText(patientName)
})
