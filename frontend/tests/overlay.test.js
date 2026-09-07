import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizedBox } from '../src/utils/overlay.js'
test('normalized coordinates take priority regardless of display size', () => {
  const box = { x1: .2549, y1: .2969, x2: .6306, y2: .9938 }
  assert.deepEqual(normalizedBox({ bbox_norm: box, bbox: { x1: 0, y1: 0, x2: 1, y2: 1 } }, { width: 1440, height: 1920 }), box)
})
test('pixel coordinates fall back to original image dimensions', () => {
  assert.deepEqual(normalizedBox({ bbox: { x1: 100, y1: 200, x2: 300, y2: 600 } }, { width: 400, height: 800 }), { x1: .25, y1: .25, x2: .75, y2: .75 })
})
test('invalid or inverted boxes do not render; out-of-bounds boxes are clipped', () => {
  assert.equal(normalizedBox({ bbox: {} }, { width: 0, height: 0 }), null)
  assert.equal(normalizedBox({ bbox_norm: { x1: .8, y1: 0, x2: .2, y2: 1 } }), null)
  assert.equal(normalizedBox({ bbox_norm: { x1: NaN, y1: 0, x2: 1, y2: 1 } }), null)
  assert.deepEqual(normalizedBox({ bbox_norm: { x1: -.1, y1: 0, x2: 1.2, y2: 1 } }), { x1: 0, y1: 0, x2: 1, y2: 1 })
})
