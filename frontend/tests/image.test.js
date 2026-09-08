import test from 'node:test'
import assert from 'node:assert/strict'
import { prepareFastImage } from '../src/utils/image.js'

test('fast image preprocessing preserves framing and leaves the original file intact', async t => {
  let dimensions = [1440, 1920]
  let fail = false
  const calls = []
  const revoked = []
  t.mock.method(URL, 'createObjectURL', () => 'blob:test')
  t.mock.method(URL, 'revokeObjectURL', url => revoked.push(url))
  const previousImage = globalThis.Image
  const previousDocument = globalThis.document
  globalThis.Image = class {
    naturalWidth = dimensions[0]
    naturalHeight = dimensions[1]
    async decode() {}
  }
  globalThis.document = {
    createElement(tag) {
      assert.equal(tag, 'canvas')
      return {
        getContext: () => ({ fillRect() {}, drawImage: (...args) => calls.push(args.slice(1)) }),
        toBlob(callback, type, quality) {
          assert.equal(type, 'image/jpeg')
          assert.equal(quality, .8)
          callback(fail ? null : new Blob(['compressed'], { type }))
        },
      }
    },
  }
  try {
    const original = new File(['original content'], 'portrait.png', { type: 'image/png' })
    for (const [width, height, expected] of [[1440, 1920, [480, 640]], [1920, 1080, [640, 360]], [320, 240, [320, 240]], [1001, 667, [640, 426]]]) {
      dimensions = [width, height]
      const output = await prepareFastImage(original)
      assert.deepEqual(calls.at(-1), [0, 0, ...expected])
      assert.equal(output.type, 'image/jpeg')
      assert.equal(output.name, 'portrait-fast.jpg')
      assert.notEqual(output, original)
    }
    assert.equal(await original.text(), 'original content')
    assert.equal(original.type, 'image/png')
    fail = true
    await assert.rejects(prepareFastImage(original), /图片压缩失败/)
    assert.equal(revoked.length, 5)
  } finally {
    if (previousImage === undefined) delete globalThis.Image
    else globalThis.Image = previousImage
    if (previousDocument === undefined) delete globalThis.document
    else globalThis.document = previousDocument
  }
})
