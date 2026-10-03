import { execFileSync, spawn } from 'node:child_process'
import { createServer } from 'node:net'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const root = resolve(frontend, '..')
const python = resolve(root, 'backend/.venv/bin/python')
process.env.PLAYWRIGHT_BROWSERS_PATH = resolve(frontend, '.cache/ms-playwright')
const children = []
let stopping = false
let dbDown
function run(command, args, extra = {}) {
  const child = spawn(command, args, { cwd: frontend, env: { ...process.env, ...extra }, stdio: ['ignore', 'pipe', 'pipe'] })
  children.push(child)
  // API/Vite sólo emiten diagnósticos técnicos; acceso HTTP y traces apagados.
  child.stdout.on('data', chunk => process.stdout.write(chunk))
  child.stderr.on('data', chunk => process.stderr.write(chunk))
  return child
}
async function stop() {
  if (stopping) return
  stopping = true
  if (dbDown?.listening) await new Promise(res => dbDown.close(res))
  await Promise.all(children.map(child => new Promise(resolveDone => {
    if (child.exitCode !== null || child.signalCode !== null) return resolveDone()
    child.once('exit', resolveDone)
    child.kill('SIGTERM')
    const timer = setTimeout(() => child.kill('SIGKILL'), 5000)
    timer.unref()
  })))
}
process.on('SIGINT', () => { void stop().then(() => process.exit(130)) })
process.on('SIGTERM', () => { void stop().then(() => process.exit(143)) })
async function port(preferred) {
  const server = createServer()
  await new Promise((res, rej) => { server.once('error', rej); server.listen(preferred ?? 0, '127.0.0.1', res) })
  const value = server.address().port
  await new Promise((res, rej) => server.close(err => err ? rej(err) : res()))
  return value
}
async function ready(url, child) {
  for (let i = 0; i < 120; i++) {
    if (child.exitCode !== null || child.signalCode !== null) throw new Error('No se pudo iniciar un servicio de pruebas')
    try {
      if ((await fetch(url)).ok) return
    } catch { /* Esperar al proceso propio. */ }
    await new Promise(res => setTimeout(res, 100))
  }
  throw new Error('Servicio local de pruebas no disponible')
}

try {
  // El helper verifica base/usuario test antes de cualquier escritura ficticia.
  const fixture = JSON.parse(execFileSync(python, [resolve(frontend, 'scripts/backend.py')], { cwd: root, encoding: 'utf8' }))
  const desired = process.env.V2_API_PORT ? Number(process.env.V2_API_PORT) : undefined
  if (desired !== undefined && (!Number.isInteger(desired) || desired < 1024 || desired > 65535)) throw new Error('V2_API_PORT inválido')
  const apiPort = await port(desired)
  const disabledPort = await port()
  const unavailablePort = await port()
  // Mantener reservado el puerto sin aceptar protocolo PostgreSQL: conexión
  // imposible real y reproducible, sin detener el contenedor compartido.
  dbDown = createServer(socket => socket.destroy())
  await new Promise((res, rej) => { dbDown.once('error', rej); dbDown.listen(0, '127.0.0.1', res) })
  const api = run(python, ['scripts/backend.py', '--serve', String(apiPort)])
  const disabled = run(python, ['scripts/backend.py', '--serve', String(disabledPort), '--demo', 'false'])
  const unavailable = run(python, ['scripts/backend.py', '--serve', String(unavailablePort), '--unavailable-db-port', String(dbDown.address().port)])
  await Promise.all([ready(`http://127.0.0.1:${apiPort}/api/v1/health/ready`, api), ready(`http://127.0.0.1:${disabledPort}/api/v1/health/ready`, disabled)])
  await ready(`http://127.0.0.1:${unavailablePort}/api/v1/health/live`, unavailable)
  const frontendPorts = await Promise.all(Array.from({ length: 4 }, () => port()))
  if (new Set(frontendPorts).size !== 4) throw new Error('Puertos de frontend repetidos; vuelva a ejecutar')
  const modes = [
    { name: 'demo', flag: 'true', backend: apiPort, command: 'dev' },
    { name: 'frontend-off', flag: 'false', backend: apiPort, command: 'dev' },
    { name: 'backend-off', flag: 'true', backend: disabledPort, command: 'dev' },
    { name: 'build', flag: 'true', backend: apiPort, command: 'preview' },
  ]
  const urls = { unavailable: `http://127.0.0.1:${unavailablePort}` }
  for (let i = 0; i < modes.length; i++) {
    const mode = modes[i]
    const server = run(process.execPath, [resolve(frontend, 'node_modules/vite/bin/vite.js'), ...(mode.command === 'preview' ? ['preview'] : []), '--port', String(frontendPorts[i])],
      { V2_API_PORT: String(mode.backend), VITE_DEMO_IDENTITY: mode.flag })
    const url = `http://127.0.0.1:${frontendPorts[i]}`
    await ready(url, server)
    urls[mode.name] = url
  }
  const runner = run(process.execPath, [resolve(frontend, 'node_modules/@playwright/test/cli.js'), 'test'], {
    V2_E2E_MANAGED: 'true', V2_E2E_URLS: JSON.stringify(urls), V2_E2E_FIXTURES: JSON.stringify(fixture),
    PLAYWRIGHT_BROWSERS_PATH: resolve(frontend, '.cache/ms-playwright'),
  })
  const code = await new Promise((res, rej) => { runner.once('error', rej); runner.once('exit', (code, signal) => res(signal ? 1 : code)) })
  if (code !== 0) throw new Error('Falló la validación de navegador')
  if (process.env.V2_CAPTURE_PREVIEW === 'true') {
    const { chromium } = await import('@playwright/test')
    const browser = await chromium.launch({ headless: true, executablePath: undefined })
    try {
      const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })
      await page.goto(urls.demo + '/patients')
      await page.getByRole('heading', { name: 'Pacientes', exact: true }).waitFor()
      const destination = resolve(root, 'docs/evidencia')
      mkdirSync(destination, { recursive: true })
      await page.screenshot({ path: resolve(destination, 'v2-03-base-escritorio.png'), fullPage: true })
      await page.setViewportSize({ width: 390, height: 844 })
      await page.screenshot({ path: resolve(destination, 'v2-03-base-movil.png'), fullPage: true })
    } finally { await browser.close() }
  }
  if (process.env.V2_CAPTURE_READ === 'true') {
    const { chromium } = await import('@playwright/test')
    const browser = await chromium.launch({ headless: true })
    try {
      const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })
      const destination = resolve(root, 'docs/evidencia')
      mkdirSync(destination, { recursive: true })
      await page.goto(urls.demo + '/patients')
      await page.getByLabel('Folio de paciente', { exact: true }).fill(fixture.patient_folio)
      await page.getByRole('button', { name: 'Buscar', exact: true }).click()
      await page.getByRole('link', { name: 'Consultar paciente ' + fixture.patient_folio }).waitFor()
      await page.screenshot({ path: resolve(destination, 'v2-04-busqueda.png'), fullPage: true })
      await page.getByRole('link', { name: 'Consultar paciente ' + fixture.patient_folio }).click()
      await page.getByRole('link', { name: 'Consultar episodio ' + fixture.admission_folio }).waitFor()
      await page.screenshot({ path: resolve(destination, 'v2-04-ficha.png'), fullPage: true })
      await page.setViewportSize({ width: 390, height: 844 })
      await page.screenshot({ path: resolve(destination, 'v2-04-ficha-movil.png'), fullPage: true })
      await page.getByRole('link', { name: 'Consultar episodio ' + fixture.admission_folio }).click()
      await page.getByText('Motivo ficticio 204', { exact: true }).waitFor()
      await page.screenshot({ path: resolve(destination, 'v2-04-episodio-movil.png'), fullPage: true })
    } finally { await browser.close() }
  }
  if (process.env.V2_CAPTURE_WRITE === 'true') {
    const { chromium } = await import('@playwright/test')
    const browser = await chromium.launch({ headless: true })
    try {
      const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })
      const destination = resolve(root, 'docs/evidencia')
      mkdirSync(destination, { recursive: true })
      await page.goto(urls.demo + '/patients/new')
      await page.getByLabel('Nombres: disponibilidad', { exact: true }).selectOption('known')
      await page.getByLabel('Nombres', { exact: true }).fill('Persona ficticia de captura V205')
      await page.getByLabel('Nacionalidad: disponibilidad').selectOption('unknown')
      await page.evaluate(() => { window.scrollTo(0, 0) })
      await page.waitForTimeout(100)
      await page.screenshot({ path: resolve(destination, 'v2-05-registro.png'), fullPage: true })
      await page.setViewportSize({ width: 390, height: 844 })
      await page.getByLabel('Tipo de identidad').selectOption('unknown')
      await page.getByLabel('Edad estimada: disponibilidad').selectOption('known')
      await page.getByLabel('Edad mínima estimada').fill('30')
      await page.getByLabel('Edad máxima estimada').fill('40')
      await page.evaluate(() => { window.scrollTo(0, 0) })
      await page.waitForTimeout(100)
      await page.screenshot({ path: resolve(destination, 'v2-05-desconocido-movil.png'), fullPage: true })
      await page.goto(urls.demo + '/patients/' + fixture.second_patient_id + '/admissions/new')
      await page.getByRole('button', { name: 'Revisar apertura' }).click()
      await page.evaluate(() => { window.scrollTo(0, 0) })
      await page.waitForTimeout(100)
      await page.screenshot({ path: resolve(destination, 'v2-05-ingreso-movil.png'), fullPage: true })
      await page.setViewportSize({ width: 1440, height: 960 })
      await page.goto(urls.demo + '/audit')
      await page.getByLabel('Actor de demostración', { exact: true }).selectOption('supervisor-demo')
      await page.getByLabel('Acción', { exact: true }).selectOption('patients.create')
      await page.getByLabel('UUID del recurso').fill(fixture.patient_id)
      await page.getByRole('button', { name: 'Consultar auditoría' }).click()
      await page.getByText('patients.create · success', { exact: true }).waitFor()
      await page.evaluate(() => { window.scrollTo(0, 0) })
      await page.waitForTimeout(100)
      await page.screenshot({ path: resolve(destination, 'v2-05-auditoria.png'), fullPage: true })
    } finally { await browser.close() }
  }
  await stop()
  const evidence = resolve(frontend, '.cache/e2e-result.json')
  const report = JSON.parse(readFileSync(evidence, 'utf8'))
  report.backend_database = 'hospital_test'
  report.fixture_references = fixture
  report.services_stopped = true
  report.frontend_modes = modes.map(m => m.name)
  // El informe JSON contiene conteos/IDs de casos; no cuerpos ni traces.
  mkdirSync(dirname(evidence), { recursive: true })
  writeFileSync(evidence, JSON.stringify(report, null, 2) + '\n')
} finally {
  await stop()
}
