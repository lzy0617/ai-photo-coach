import test from 'node:test'
import assert from 'node:assert/strict'
import { analyzeFast } from '../src/api/photography.js'

test('all analysis callers serialize; canceled waiters never send; errors release the lock', async t => {
  const pending = []
  let active = 0, maximum = 0, requests = 0
  t.mock.method(globalThis, 'fetch', async () => {
    requests++; active++; maximum = Math.max(maximum, active)
    return new Promise(resolve => pending.push(ok => {
      active--
      resolve({ ok, status: ok ? 200 : 503, json: async () => ({ composition: {}, detection: { persons: [] } }) })
    }))
  })
  const file = new File(['frame'], 'camera.jpg', { type: 'image/jpeg' })
  const first = analyzeFast(file)
  const stopped = new AbortController()
  const canceled = analyzeFast(file, { signal: stopped.signal })
  const canceledCheck = assert.rejects(canceled, { name: 'AbortError' })
  const next = analyzeFast(file)
  stopped.abort()
  assert.equal(requests, 1)
  pending.shift()(true)
  await first
  await canceledCheck
  assert.equal(requests, 2)
  const nextCheck = assert.rejects(next, /503/)
  pending.shift()(false)
  await nextCheck
  const retry = analyzeFast(file)
  assert.equal(requests, 3)
  pending.shift()(true)
  await retry
  assert.equal(maximum, 1)
})
