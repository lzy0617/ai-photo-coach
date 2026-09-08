import test from 'node:test'
import assert from 'node:assert/strict'
import { initialStability, nextStability } from '../src/utils/liveStability.js'
const result = (score, count = 1) => ({ composition: { score, status: count ? 'ok' : 'no_person' }, detection: { persons: Array.from({ length: count }, () => ({})) } })
test('two consecutive high scores enter stability; 75–79 preserve it and 74 exits', () => {
  let state = initialStability()
  for (const [score, expected] of [[80, false], [79, false], [80, false], [81, true], [79, true], [75, true], [74, false], [81, false], [80, true]]) {
    state = nextStability(state, result(score))
    assert.equal(state.stable, expected, `score ${score}`)
  }
})
test('no-person, multiple people and missing scores reset single-person stability', () => {
  for (const invalid of [result(90, 0), result(90, 2), result(undefined), null]) {
    const state = nextStability({ stable: true, highCount: 2 }, invalid)
    assert.deepEqual(state, initialStability())
    assert.equal(nextStability(state, result(90)).stable, false)
  }
})
