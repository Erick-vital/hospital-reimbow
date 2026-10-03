import { defineConfig } from '@playwright/test'
import path from 'node:path'

if (process.env.V2_E2E_MANAGED !== 'true') throw new Error('Use npm run test:e2e: la prueba requiere servicios propios sobre hospital_test')

export default defineConfig({
  testDir: './tests',
  workers: 1,
  retries: 0,
  timeout: 30_000,
  forbidOnly: true,
  reporter: [['list'], [path.resolve('tests/reporter.mjs')]],
  use: { headless: true, trace: 'off', screenshot: 'off', video: 'off' },
  outputDir: '.cache/test-results',
})
