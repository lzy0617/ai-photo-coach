import test from 'node:test'
import assert from 'node:assert/strict'
import { savePhoto } from '../src/utils/savePhoto.js'
test('saving downloads the original even when native sharing is supported, and releases the URL', async t => {
  const file = new File(['original'], 'photo.jpg', { type: 'image/jpeg' })
  const previousNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  const previousDocument = globalThis.document
  const events = []
  let cleanup
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { canShare: () => true, share: () => { assert.fail('保存照片不应打开分享面板') } } })
  const anchor = { click() { events.push('click') }, remove() { events.push('remove') } }
  globalThis.document = { createElement: () => anchor, body: { appendChild() {} } }
  t.mock.method(URL, 'createObjectURL', value => { assert.equal(value, file); return 'blob:original' })
  t.mock.method(URL, 'revokeObjectURL', value => events.push(value))
  t.mock.method(globalThis, 'setTimeout', callback => { cleanup = callback })
  try {
    assert.match(await savePhoto(file), /下载/)
    assert.equal(anchor.download, file.name)
    assert.equal(anchor.href, 'blob:original')
    assert.deepEqual(events, ['click', 'remove'])
    cleanup()
    assert.equal(events.at(-1), 'blob:original')
  } finally {
    if (previousNavigator) Object.defineProperty(globalThis, 'navigator', previousNavigator); else delete globalThis.navigator
    if (previousDocument === undefined) delete globalThis.document; else globalThis.document = previousDocument
  }
})
