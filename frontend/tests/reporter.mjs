import { mkdirSync, writeFileSync } from 'node:fs'

export default class Report {
  onBegin(_config, suite) { this.total = suite.allTests().length; this.cases = [] }
  onTestEnd(test, result) { this.cases.push({ case: test.title, status: result.status, duration_ms: result.duration }) }
  onEnd(result) {
    mkdirSync('.cache', { recursive: true })
    writeFileSync('.cache/e2e-result.json', JSON.stringify({ date_utc: new Date().toISOString(), total: this.total, status: result.status, cases: this.cases }, null, 2) + '\n')
  }
}
