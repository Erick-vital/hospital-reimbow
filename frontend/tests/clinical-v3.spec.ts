import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
const urls = JSON.parse(process.env.V2_E2E_URLS!)
const fixture = JSON.parse(process.env.V2_E2E_FIXTURES!)
const banner = (page: Page) => page.getByRole('region', { name: 'Contexto clínico actual' })
async function navigate(page: Page, path: string) {
  await page.evaluate(path => { history.pushState(null, '', path); dispatchEvent(new PopStateEvent('popstate')) }, path)
}
async function start(page: Page, path = '/clinical/attentions', actor = 'medico-demo') {
  await page.goto(urls.demo + path)
  await page.getByLabel('Actor de demostración', { exact: true }).selectOption(actor)
  await expect(page.getByRole('region', {name:'Acceso actual'})).toContainText(actor)
}
async function clean(page: Page) {
  expect(await page.evaluate(async () => [localStorage.length, sessionStorage.length, (await indexedDB.databases()).length, (await caches.keys()).length, (await navigator.serviceWorker.getRegistrations()).length])).toEqual([0,0,0,0,0])
}

test('C02 · lista real, paginación, filtros y pareja de catálogos', async ({ page }) => {
  await start(page)
  await expect(page.getByRole('heading', { name: 'Atenciones abiertas', exact: true })).toBeFocused()
  const first = page.waitForResponse(response => response.url().includes('/api/v3/clinical/attentions?') && response.url().includes('limit=5'))
  await page.getByLabel('Atenciones por página').selectOption('5')
  const body = await (await first).json()
  expect(body.total).toBeGreaterThan(5)
  const list = page.getByRole('list', { name: 'Atenciones abiertas' })
  for (const item of body.items) await expect(list.getByRole('link', { name: 'Abrir atención ' + item.episode.folio })).toBeVisible()
  const next = page.waitForResponse(response => response.url().includes('/api/v3/clinical/attentions?') && response.url().includes('offset=5'))
  await page.getByRole('button', { name: 'Siguiente', exact: true }).click()
  const nextBody = await (await next).json()
  for (const item of nextBody.items) expect(body.items.some((old: { episode: { id: string } }) => old.episode.id === item.episode.id)).toBe(false)
  await page.getByLabel('Tipo de atención').selectOption('outpatient')
  await page.getByRole('combobox', { name: 'Sede', exact: true }).selectOption(fixture.clinical_site_id)
  await expect(page.getByRole('combobox', { name: 'Servicio', exact: true })).toBeEnabled()
  await page.getByRole('combobox', { name: 'Servicio', exact: true }).selectOption(fixture.clinical_service_id)
  await expect(list).toContainText(fixture.patient_folio)
  const filtered = await page.evaluate(async ({site, service}) => {
    const response = await fetch(`/api/v3/clinical/attentions?type=outpatient&site_id=${site}&service_id=${service}`, { cache:'no-store', headers:{'X-Dev-Actor':'medico-demo'} })
    return response.json()
  }, {site:fixture.clinical_site_id, service:fixture.clinical_service_id})
  expect(filtered.items.every((item: { episode: { type: string; site: { value: { id: string } }; service: { value: { id: string } } } }) => item.episode.type === 'outpatient' && item.episode.site.value.id === fixture.clinical_site_id && item.episode.service.value.id === fixture.clinical_service_id)).toBe(true)
  await page.getByRole('combobox', { name: 'Sede', exact: true }).selectOption('')
  await expect(page.getByRole('combobox', { name: 'Servicio', exact: true })).toHaveValue('')
  await expect(page.getByText('El filtro de servicio se limpió al cambiar sede.')).toBeVisible()
  await clean(page)
})

test('C03 · episodio, longitudinal, otra atención, otro paciente y atrás', async ({ page }) => {
  await start(page, '/clinical/attentions/' + fixture.admission_id)
  await expect(banner(page)).toContainText(fixture.patient_folio)
  await expect(banner(page)).toContainText(fixture.admission_folio)
  await expect(page.getByText('Motivo ficticio 204', { exact: true })).toHaveCount(0)
  await expect(page.getByText('1990-01-01', { exact: true })).toHaveCount(0)
  await page.getByRole('link', { name: 'Consultar vista longitudinal ' + fixture.patient_folio }).click()
  await expect(banner(page)).toContainText('Sin episodio seleccionado')
  await expect(page.getByRole('list', { name: 'Atenciones del paciente' }).getByRole('link')).toHaveCount(7)
  await page.getByRole('link', { name: 'Abrir atención ' + fixture.admission_folio }).click()
  await expect(banner(page)).toContainText(fixture.admission_folio)
  await navigate(page, '/clinical/attentions/' + fixture.clinical_outpatient_id)
  await expect(banner(page)).toContainText('Consulta externa')
  await navigate(page, '/clinical/attentions/' + fixture.clinical_second_episode_id)
  await expect(banner(page)).toContainText(fixture.clinical_second_patient_folio)
  await expect(banner(page)).not.toContainText(fixture.patient_folio)
  await page.goBack()
  await expect(banner(page)).toContainText(fixture.patient_folio)
  await expect(banner(page)).toContainText('Consulta externa')
  await clean(page)
})

test('C03 · contexto tardío de otro paciente no repuebla la vista', async ({ page }) => {
  await start(page)
  let captured!: () => void
  let release!: () => void
  const received = new Promise<void>(resolve => { captured = resolve })
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/v3/clinical/attentions/' + fixture.admission_id + '/context', async route => {
    const response = await route.fetch(); captured(); await gate
    try { await route.fulfill({ response }) } catch { /* Contexto cancelado. */ }
  })
  await navigate(page, '/clinical/attentions/' + fixture.admission_id)
  await received
  await navigate(page, '/clinical/attentions/' + fixture.clinical_second_episode_id)
  await expect(banner(page)).toContainText(fixture.clinical_second_patient_folio)
  release(); await page.unrouteAll({ behavior:'wait' })
  await expect(banner(page)).not.toContainText(fixture.patient_folio)
  await clean(page)
})

test('C03/C04 · cambio de actor, recarga y URL directa comprueban acceso', async ({ page }) => {
  await start(page, '/clinical/attentions/' + fixture.admission_id, 'enfermeria-demo')
  await expect(banner(page)).toContainText(fixture.patient_folio)
  await page.getByLabel('Actor de demostración', { exact: true }).selectOption('consulta-demo')
  await expect(banner(page)).toHaveCount(0)
  await expect(page.getByRole('heading', { name:'Acceso no disponible' })).toBeVisible()
  const denied = await page.evaluate(async id => {
    const response = await fetch('/api/v3/clinical/attentions/' + id + '/context', { cache:'no-store', headers:{'X-Dev-Actor':'consulta-demo', 'X-Role':'medico-demo'} })
    return {status:response.status, body:await response.json()}
  },fixture.admission_id)
  expect(denied.status).toBe(403)
  expect(JSON.stringify(denied.body)).not.toContain(fixture.patient_folio)
  await page.getByLabel('Actor de demostración', { exact: true }).selectOption('medico-demo')
  await expect(banner(page)).toContainText(fixture.patient_folio)
  await page.reload()
  // La identidad de demostración sólo vive en memoria; recarga regresa a Admisión.
  await expect(banner(page)).toHaveCount(0)
  await expect(page.getByRole('heading', { name:'Acceso no disponible' })).toBeVisible()
  await page.getByLabel('Actor de demostración', { exact: true }).selectOption('medico-demo')
  await expect(banner(page)).toContainText(fixture.patient_folio)
  await clean(page)
})

test('C04 · 403 real, recuperación, 404 y paciente sin atenciones', async ({ page }) => {
  await start(page)
  await page.route('**/api/v3/clinical/attentions/' + fixture.admission_id + '/context', async route => {
    const response = await route.fetch({ headers:{...route.request().headers(), 'x-dev-actor':'consulta-demo'} })
    await route.fulfill({response})
  })
  await navigate(page, '/clinical/attentions/' + fixture.admission_id)
  await expect(page.getByRole('heading', { name:'Acceso no disponible' })).toBeVisible()
  await expect(banner(page)).toHaveCount(0)
  await page.unrouteAll()
  await page.getByRole('button', {name:'Revalidar acceso'}).click()
  await expect(banner(page)).toContainText(fixture.patient_folio)
  await navigate(page, '/clinical/attentions/ffffffff-ffff-4fff-afff-ffffffffffff')
  await expect(page.getByRole('heading', {name:'Registro no encontrado'})).toBeVisible()
  await expect(banner(page)).toHaveCount(0)
  await navigate(page, '/clinical/patients/' + fixture.second_patient_id)
  await expect(banner(page)).toContainText('Vista longitudinal')
  await expect(page.getByText('Sin atenciones en esta página.', {exact:true})).toBeVisible()
  await expect(page.getByText('Esta etapa permite consultar la identificación y las atenciones.', {exact:false})).toBeVisible()
})

test('C03 · teclado, foco, cabecera permanente y móvil', async ({ page }) => {
  await page.setViewportSize({width:390, height:844})
  await start(page, '/clinical/attentions/' + fixture.admission_id)
  await expect(page.getByRole('heading', {name:'Contexto de la atención'})).toBeFocused()
  await expect(banner(page)).toContainText(fixture.patient_folio)
  await expect(banner(page)).toContainText(fixture.admission_folio)
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', {name:'Volver a atenciones abiertas'})).toBeFocused()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.evaluate(() => scrollTo(0, document.body.scrollHeight))
  const bounds = await banner(page).boundingBox()
  expect(bounds).not.toBeNull()
  expect(bounds!.y).toBeGreaterThanOrEqual(0)
  await clean(page)
})
