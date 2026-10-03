import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

const urls = JSON.parse(process.env.V2_E2E_URLS!)
const fixture = JSON.parse(process.env.V2_E2E_FIXTURES!)
const uuid = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i
const path = '/patients/' + fixture.second_patient_id + '/admissions/new'
async function open(page: Page) {
  await page.goto(urls.demo + path)
  await page.getByRole('button', { name: 'Revisar apertura' }).click()
  await page.getByRole('button', { name: 'Confirmar apertura' }).click()
}
async function oneCreation(page: Page, id: string) {
  const response = await page.request.get(urls.demo + `/api/v1/audit?resource_id=${id}&action=admissions.create`, { headers: { 'X-Dev-Actor': 'supervisor-demo' } })
  expect(response.status()).toBe(200)
  expect((await response.json()).total).toBe(1)
}
async function emptyStorage(page: Page) {
  expect(await page.evaluate(async () => [localStorage.length, sessionStorage.length, (await indexedDB.databases()).length, (await caches.keys()).length])).toEqual([0,0,0,0])
}

test('R01 · PostgreSQL inaccesible real, correlación y recuperación con mismo intento', async ({ page }) => {
  const sent: { key: string; body: string }[] = []
  await page.route('**/api/v2/admissions', async route => {
    sent.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! })
    const response = await route.fetch(sent.length === 1 ? { url: urls.unavailable + '/api/v2/admissions' } : {})
    expect(response.status()).toBe(sent.length === 1 ? 503 : 201)
    if (sent.length === 1) {
      expect(response.headers()['x-request-id']).toMatch(uuid)
      expect(response.headers()['cache-control']).toBe('no-store')
      expect(JSON.stringify(await response.json())).not.toMatch(/postgresql|password|SELECT|Traceback/)
    }
    await route.fulfill({ response })
  })
  await open(page)
  await expect(page.getByRole('alert')).toContainText('DATABASE_UNAVAILABLE')
  await expect(page.getByRole('alert')).toContainText(/Referencia de la solicitud: [0-9a-f-]{36}/)
  await expect(page.getByLabel('Tipo de atención')).toBeDisabled()
  await page.getByRole('button', { name: 'Reintentar el mismo intento' }).click()
  await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toBeVisible()
  expect(sent).toHaveLength(2); expect(sent[0]).toEqual(sent[1])
  await emptyStorage(page)
})

test('R02 · dos peticiones HTTP simultáneas, mismo recurso y creación única', async ({ page }) => {
  let id!: string
  await page.route('**/api/v2/admissions', async route => {
    // Ambas peticiones salen de una misma barrera; Promise.all no espera una
    // respuesta para enviar la otra. I06 backend añade barrera dentro de SQL.
    let release!: () => void
    const gate = new Promise<void>(done => { release = done })
    const first = gate.then(() => route.fetch())
    const second = gate.then(() => page.request.post(route.request().url(), {
      headers: route.request().headers(), data: route.request().postData()!,
    }))
    release()
    const responses = await Promise.all([first, second])
    expect(responses.map(r => r.status()).sort()).toEqual([200,201])
    const resources = await Promise.all(responses.map(r => r.json()))
    id = resources[0].id; expect(resources[1].id).toBe(id)
    expect(responses[0].headers()['x-request-id']).not.toBe(responses[1].headers()['x-request-id'])
    await route.fulfill({ response: responses[0] })
  })
  await open(page)
  await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toBeVisible()
  await oneCreation(page, id)
})

test('R03 · timeout después de commit y replay conservan cuerpo/clave', async ({ page }) => {
  const sent: { key: string; body: string }[] = []
  let id!: string
  let release!: () => void
  const gate = new Promise<void>(done => { release = done })
  await page.route('**/api/v2/admissions', async route => {
    sent.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! })
    const response = await route.fetch()
    if (sent.length === 1) {
      expect(response.status()).toBe(201); id = (await response.json()).id
      await gate
      try { await route.fulfill({ response }) } catch { /* Cliente agotó plazo. */ }
    } else {
      expect(response.status()).toBe(200); expect((await response.json()).id).toBe(id)
      await route.fulfill({ response })
    }
  })
  try {
    await open(page)
    await expect(page.getByRole('alert')).toContainText('TIMEOUT', { timeout: 12_000 })
    release()
    await page.getByRole('button', { name: 'Reintentar el mismo intento' }).click()
    await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toBeVisible()
    expect(sent).toHaveLength(2); expect(sent[0]).toEqual(sent[1])
    await oneCreation(page, id)
  } finally { release(); await page.unrouteAll({ behavior: 'wait' }) }
})

test('R04 · vencimiento real de clave exige reconciliar sin repetir creación', async ({ page }) => {
  let key!: string
  let id!: string
  let count = 0
  await page.route('**/api/v2/admissions', async route => {
    count++; key = route.request().headers()['idempotency-key']
    const response = await route.fetch()
    if (count === 1) {
      expect(response.status()).toBe(201); id = (await response.json()).id
      return route.abort('connectionfailed')
    }
    expect(response.status()).toBe(409)
    await route.fulfill({ response })
  })
  await open(page)
  await expect(page.getByRole('button', { name: 'Reintentar el mismo intento' })).toBeVisible()
  execFileSync(resolve('../backend/.venv/bin/python'), [resolve('scripts/backend.py'), '--expire-key', key], { cwd: resolve('..'), stdio: 'pipe' })
  await page.getByRole('button', { name: 'Reintentar el mismo intento' }).click()
  await expect(page.getByRole('alert')).toContainText('IDEMPOTENCY_EXPIRED')
  await expect(page.getByRole('link', { name: 'Consultar y reconciliar registros' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Reintentar el mismo intento' })).toHaveCount(0)
  expect(count).toBe(2); await oneCreation(page, id)
})

test('R05 · desconocido tras commit perdido/recarga muestra reconciliación y supervisor', async ({ page }) => {
  let count = 0
  await page.route('**/api/v2/patients', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    count++
    const response = await route.fetch(); expect(response.status()).toBe(201)
    return route.abort('connectionfailed')
  })
  await page.goto(urls.demo + '/patients/new')
  await page.getByLabel('Tipo de identidad').selectOption('unknown')
  await page.getByRole('button', { name: 'Buscar coincidencias del borrador' }).click()
  await page.getByLabel('Revisé las coincidencias').check()
  await page.getByRole('button', { name: 'Revisar registro' }).click()
  await page.getByRole('button', { name: 'Confirmar registro' }).click()
  await expect(page.getByRole('button', { name: 'Reintentar el mismo intento' })).toBeVisible()
  await page.reload()
  const notice = page.getByRole('complementary', { name: 'Recuperación de un alta anterior' })
  await expect(notice).toContainText('no cancela un alta que el servidor ya recibió')
  await expect(notice).toContainText('solicita revisión al supervisor')
  await expect(notice.getByRole('link', { name: 'Buscar un paciente ya registrado' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Reintentar el mismo intento' })).toHaveCount(0)
  expect(count).toBe(1); await emptyStorage(page)
})

test('R06 · cambiar actor tras commit descarta resultado tardío sin repetir envío', async ({ page }) => {
  let release!: () => void
  let captured!: () => void
  let count = 0
  const gate = new Promise<void>(done => { release = done })
  const received = new Promise<void>(done => { captured = done })
  await page.route('**/api/v2/admissions', async route => {
    count++
    const response = await route.fetch(); expect(response.status()).toBe(201)
    captured(); await gate
    try { await route.fulfill({ response }) } catch { /* Actor anterior cancelado. */ }
  })
  try {
    await open(page); await received
    await page.getByLabel('Actor de demostración', { exact: true }).selectOption('supervisor-demo')
    await expect(page.getByRole('complementary', { name: 'Recuperación de un alta anterior' })).toBeVisible()
    release(); await page.unrouteAll({ behavior: 'wait' })
    await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Reintentar el mismo intento' })).toHaveCount(0)
    expect(count).toBe(1); await emptyStorage(page)
  } finally { release(); await page.unrouteAll({ behavior: 'wait' }) }
})

test('R07 · teclado, foco de confirmación e identidad móvil visible al desplazarse', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(urls.demo + path)
  const type = page.getByLabel('Tipo de atención')
  await type.focus(); await page.keyboard.press('ArrowDown')
  await expect(type).toHaveValue('outpatient')
  await page.keyboard.press('ArrowUp'); await expect(type).toHaveValue('emergency')
  const review = page.getByRole('button', { name: 'Revisar apertura' })
  await review.focus(); await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Confirmar apertura' })).toBeFocused()
  await expect(page.getByText('Confirmar paciente y atención')).toBeVisible()
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  const banner = page.getByRole('region', { name: 'Paciente del contexto actual' })
  await expect(banner).toContainText('Beta')
  const bounds = await banner.boundingBox()
  expect(bounds!.y).toBeGreaterThanOrEqual(0); expect(bounds!.y + bounds!.height).toBeLessThan(844)
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Episodio abierto' })).toBeVisible()
})
