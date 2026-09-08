import test from 'node:test'
import assert from 'node:assert/strict'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { useCamera } from '../src/composables/useCamera.js'

test('camera frames are scaled directly to JPEG 0.75 without crop or upscale', async () => {
  let camera
  await renderToString(createSSRApp({ setup() { camera = useCamera(); return () => null } }))
  const previous = globalThis.document
  const draws = []
  let expectedQuality = .75
  globalThis.document = { createElement: () => ({
    getContext: () => ({ drawImage: (...args) => draws.push(args.slice(1)) }),
    toBlob(callback, type, quality) {
      assert.equal(type, 'image/jpeg'); assert.equal(quality, expectedQuality)
      callback(new Blob(['jpeg'], { type }))
    },
  }) }
  try {
    for (const [width, height, expected] of [[1920, 1080, [640, 360]], [1080, 1920, [360, 640]], [320, 240, [320, 240]]]) {
      const frame = await camera.capture({ videoWidth: width, videoHeight: height, readyState: 2 })
      assert.deepEqual(draws.at(-1), [0, 0, ...expected])
      assert.equal(frame.type, 'image/jpeg')
    }
    expectedQuality = .92
    const photo = await camera.capturePhoto({ videoWidth: 1920, videoHeight: 1080, readyState: 2 })
    assert.deepEqual(draws.at(-1), [0, 0, 1920, 1080])
    assert.equal(photo.type, 'image/jpeg')
    assert.match(photo.name, /^photo-/)
    await assert.rejects(camera.capture({ videoWidth: 0 }), /尚未就绪/)
  } finally {
    if (previous === undefined) delete globalThis.document
    else globalThis.document = previous
  }
})

test('a late permission grant after stop releases tracks instead of reopening camera', async () => {
  let camera
  await renderToString(createSSRApp({ setup() { camera = useCamera(); return () => null } }))
  const previousWindow = Object.getOwnPropertyDescriptor(globalThis, 'window')
  const previousNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  let grant, stopped = 0
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { isSecureContext: true } })
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: {
    getUserMedia(options) {
      assert.deepEqual(options, { video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false })
      return new Promise(resolve => { grant = resolve })
    },
  } } })
  try {
    const start = camera.start()
    camera.stop()
    grant({ getTracks: () => [{ stop() { stopped++ } }] })
    assert.equal(await start, null)
    assert.equal(stopped, 1)
    assert.equal(camera.stream.value, null)
  } finally {
    if (previousWindow) Object.defineProperty(globalThis, 'window', previousWindow)
    else delete globalThis.window
    if (previousNavigator) Object.defineProperty(globalThis, 'navigator', previousNavigator)
    else delete globalThis.navigator
  }
})

test('hardware zoom detects support, clamps constraints, and falls back without closing camera', async () => {
  let camera
  await renderToString(createSSRApp({ setup() { camera = useCamera(); return () => null } }))
  const oldWindow = Object.getOwnPropertyDescriptor(globalThis, 'window')
  const oldNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  let actual = 1, rejectZoom = false, stopped = 0
  const requests = []
  const track = {
    getCapabilities: () => ({ zoom: { min: 1, max: 3, step: .5 } }),
    getSettings: () => ({ zoom: actual, facingMode: requests.at(-1).video.facingMode.ideal }),
    applyConstraints: async options => { if (rejectZoom) throw new Error('unsupported'); actual = options.advanced[0].zoom },
    stop: () => { stopped++ },
  }
  const stream = { getTracks: () => [track], getVideoTracks: () => [track] }
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { isSecureContext: true } })
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: {
    getUserMedia: async options => { requests.push(options); return stream },
  } } })
  try {
    await camera.start()
    assert.equal(camera.zoomSupported.value, true)
    await camera.setZoom(10)
    assert.equal(actual, 3)
    await camera.setZoom(1.7)
    assert.equal(actual, 1.5)
    rejectZoom = true
    await camera.setZoom(2)
    assert.equal(camera.zoomSupported.value, false)
    assert.ok(camera.stream.value)
    assert.equal(stopped, 0)
    await camera.start('user')
    assert.equal(stopped, 1)
    assert.equal(camera.facingMode.value, 'user')
    delete track.getCapabilities
    await camera.start('environment')
    assert.equal(camera.zoomSupported.value, false)
    assert.ok(camera.stream.value)
    camera.stop()
  } finally {
    if (oldWindow) Object.defineProperty(globalThis, 'window', oldWindow)
    else delete globalThis.window
    if (oldNavigator) Object.defineProperty(globalThis, 'navigator', oldNavigator)
    else delete globalThis.navigator
  }
})
