const base = (import.meta.env.VITE_API_BASE || '').trim().replace(/\/+$/, '')
async function request(path, options = {}, timeout = 30000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  try {
    const response = await fetch(`${base}${path}`, { ...options, signal: controller.signal })
    if (!response.ok) throw new Error(`服务请求失败（${response.status}），请稍后重试。`)
    const data = await response.json()
    return data
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('请求超时，请确认边缘设备在线后重试。')
    if (error instanceof TypeError) throw new Error('无法连接边缘设备，请检查网络和 API 地址后重试。')
    if (error instanceof SyntaxError) throw new Error('服务返回格式异常，请检查 API 地址或代理配置。')
    throw error
  } finally { clearTimeout(timer) }
}
export async function checkHealth() {
  const data = await request('/health', {}, 6000)
  if (data.status !== 'ok') throw new Error('边缘服务尚未就绪')
  return data
}
export async function analyzeFast(image) {
  const body = new FormData()
  body.append('image', image)
  const data = await request('/api/analyze-fast', { method: 'POST', body })
  if (!data.composition || !Array.isArray(data.detection?.persons)) throw new Error('分析结果不完整，请重试。')
  return data
}
// 云端接口确定后在此实现；当前不会发送请求。
export async function requestDeepReview() {
  throw new Error('AI 深度点评即将支持')
}
