const base = (import.meta.env?.VITE_API_BASE || '').trim().replace(/\/+$/, '')
async function request(path, options = {}, timeout = 30000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  try {
    const response = await fetch(`${base}${path}`, { ...options, signal: controller.signal })
    if (!response.ok) throw new Error(`服务请求失败（${response.status}），请稍后重试。`)
    const data = await response.json()
    return data
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('请求超时，请确认分析服务在线后重试。')
    if (error instanceof TypeError) throw new Error('无法连接分析服务，请检查网络和 API 地址后重试。')
    if (error instanceof SyntaxError) throw new Error('服务返回格式异常，请检查 API 地址或代理配置。')
    throw error
  } finally { clearTimeout(timer) }
}
export async function checkHealth() {
  const data = await request('/health', {}, 6000)
  if (data.status !== 'ok') throw new Error('分析服务尚未就绪')
  return data
}
// 所有快速分析（实时、模拟照片、诊断）共享互斥锁。
// 已发送的请求自然结束，避免暂停后立即重发造成服务端推理堆积。
let analysisInFlight = null
export async function analyzeFast(image, { signal } = {}) {
  while (analysisInFlight) {
    try { await analysisInFlight } catch { /* 前一个调用的错误由其调用者处理 */ }
    signal?.throwIfAborted()
  }
  signal?.throwIfAborted()
  const operation = (async () => {
    const body = new FormData()
    body.append('image', image)
    const data = await request('/api/analyze-fast', { method: 'POST', body })
    if (!data.composition || !Array.isArray(data.detection?.persons)) throw new Error('分析结果不完整，请重试。')
    return data
  })()
  analysisInFlight = operation
  try { return await operation }
  finally { if (analysisInFlight === operation) analysisInFlight = null }
}
// 深度分析与实时 YOLO 使用不同的锁；连续点击复用同一个在途请求。
let deepAnalysisInFlight = null
export async function requestDeepReview(image, metrics) {
  if (deepAnalysisInFlight) {
    if (deepAnalysisInFlight.image === image && deepAnalysisInFlight.metrics === metrics) return deepAnalysisInFlight.operation
    throw new Error('已有一项 AI 深度分析正在进行，请稍后重试。')
  }
  const operation = (async () => {
    const body = new FormData()
    body.append('image', image, image.name || 'frame.jpg')
    body.append('metrics', JSON.stringify(metrics))
    const data = await request('/api/deep-analyze', { method: 'POST', body }, 120000)
    if (data.mode !== 'deep' || typeof data.success !== 'boolean' || !data.fast_analysis) {
      throw new Error('AI 深度分析结果不完整，请重试。')
    }
    if (data.success && !data.deep_analysis) throw new Error('AI 深度分析结果不完整，请重试。')
    return data
  })()
  deepAnalysisInFlight = { image, metrics, operation }
  try { return await operation }
  finally { if (deepAnalysisInFlight?.operation === operation) deepAnalysisInFlight = null }
}
