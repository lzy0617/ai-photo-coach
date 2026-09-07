import test from 'node:test'
import assert from 'node:assert/strict'
import { friendlyText, dimensionPresentation, brightnessPresentation, guideStatus } from '../src/utils/presentation.js'

test('engineering suggestions become gentle actions without movement percentages', () => {
  assert.equal(friendlyText('建议人物向左移动约 12% 画面宽度'), '可以尝试让人物稍向左移动。')
  assert.equal(friendlyText('建议人物向右移动约 8% 画面宽度'), '可以尝试让人物稍向右移动。')
  assert.equal(friendlyText('建议减少人物上方空白区域'), '可以尝试减少一些上方留白。')
  assert.equal(friendlyText('头顶留白较自然'), '上方留白较自然')
  assert.equal(friendlyText('新的后端建议'), '新的后端建议')
  assert.equal(friendlyText(null), '')
})
test('dimension states reflect comments, not a new quality score threshold', () => {
  assert.equal(dimensionPresentation('position', { style: 'centered', score: 95 }).state, '居中稳定')
  assert.equal(dimensionPresentation('headroom', { comment: '顶部留白较多', score: 45 }).state, '偏多')
  assert.equal(dimensionPresentation('subject_size', { comment: '人物主体占画面比例较合适' }).state, '合适')
  assert.equal(dimensionPresentation('position', null).state, '等待分析')
})
test('brightness preserves creative intent and never exposes a quality score', () => {
  const data = brightnessPresentation({ tendency: 'dark', score: 45, dark_ratio: .68 })
  assert.match(data.comment, /低调氛围/)
  assert.deepEqual(data.notes, ['暗部占比较高'])
  assert.equal(data.score, undefined)
  assert.equal(brightnessPresentation({ status: 'error', tendency: 'dark' }).state, '暂不可用')
  assert.equal(brightnessPresentation({ tendency: 'unknown', comment: '新的状态' }).comment, '新的状态')
})
test('multi-person and missing-person states take priority over stable composition', () => {
  const result = { composition: { suggestions: ['当前基础构图较稳定，可以进一步关注背景与光线'] } }
  assert.equal(guideStatus(result, false, false), '关系较稳定')
  assert.equal(guideStatus(result, false, true), '多人位置参考')
  assert.equal(guideStatus(result, true, false), '等待清晰人物')
  assert.equal(guideStatus(null, false, false), '等待取景')
})
