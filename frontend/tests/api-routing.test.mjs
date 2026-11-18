import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

async function moduleUrl(path) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8')
  return ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}
const dataUrl = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
const apiUrl = dataUrl(await moduleUrl('../src/services/api.ts'))
const mapSource = (await moduleUrl('../src/services/mapData.ts'))
  .replace(/(['"])\.\/api\1/, JSON.stringify(apiUrl))
const { loadMapData } = await import(dataUrl(mapSource))
const { formatIndicatorValue } = await import(dataUrl(await moduleUrl('../src/services/indicatorLabels.ts')))

test('risk results use the prediction API while GDP uses World Bank', async () => {
  const originalFetch = globalThis.fetch
  const requests = []
  globalThis.fetch = async path => {
    requests.push(path)
    return new Response('{}', { status: 200 })
  }
  try {
    await loadMapData('default-risk', 2025)
    await loadMapData('NY.GDP.MKTP.KD.ZG', 2025)
    assert.equal(requests[0], '/api/data/map?indicator=default-risk&year=2025')
    assert.equal(requests[1], '/api/live/world-bank/map?indicator=NY.GDP.MKTP.KD.ZG&year=2025')
    assert.equal(formatIndicatorValue(0.125, 'default-risk'), '12.5%')
    assert.equal(formatIndicatorValue(0, 'default-risk'), '0.0%')
  } finally {
    globalThis.fetch = originalFetch
  }
})
