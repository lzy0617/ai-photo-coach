// 单人人像的几何参考状态；仅在收到一份新的有效分析结果时推进。
export const initialStability = () => ({ stable: false, highCount: 0 })
export function nextStability(previous, result) {
  const score = result?.composition?.score
  if (result?.detection?.persons?.length !== 1 || result?.composition?.status === 'no_person' || !Number.isFinite(score)) return initialStability()
  if (score < 75) return initialStability()
  if (previous.stable) return { stable: true, highCount: 0 }
  const highCount = score >= 80 ? previous.highCount + 1 : 0
  return { stable: highCount >= 2, highCount }
}
