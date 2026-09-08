import test from 'node:test'
import assert from 'node:assert/strict'
import { analyzeFast, requestDeepReview } from '../src/api/photography.js'

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

test('rapid deep-analysis calls share one request and send the latest YOLO metrics', async t => {
  let requests = 0, release, sentMetrics
  t.mock.method(globalThis, 'fetch', async (_url, options) => {
    requests++
    sentMetrics = JSON.parse(options.body.get('metrics'))
    assert.equal(options.body.get('image').name, 'keyframe.jpg')
    return new Promise(resolve => { release = () => resolve({
      ok: true,
      json: async () => ({ success: true, mode: 'deep', fast_analysis: sentMetrics, deep_analysis: { suggestions: [] } }),
    }) })
  })
  const image = new File(['frame'], 'keyframe.jpg', { type: 'image/jpeg' })
  const metrics = { detection: { persons: [{}] }, composition: { score: 80 } }

  const first = requestDeepReview(image, metrics)
  const repeated = requestDeepReview(image, metrics)
  assert.equal(requests, 1)
  release()

  assert.deepEqual((await first).fast_analysis, metrics)
  assert.deepEqual((await repeated).deep_analysis, { suggestions: [] })
  assert.equal(requests, 1)
})
