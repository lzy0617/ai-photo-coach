import { onUnmounted, ref } from 'vue'

export function useCamera() {
  const stream = ref(null)
  const facingMode = ref('environment'), cameraNotice = ref('')
  const zoomSupported = ref(false), zoom = ref(1), zoomMin = ref(1), zoomMax = ref(1), zoomStep = ref(.1), zoomBusy = ref(false)
  function readControls(track) {
    zoomSupported.value = false
    try {
      const range = track?.getCapabilities?.().zoom
      if (!range || typeof track.applyConstraints !== 'function' || !Number.isFinite(range.min) || !Number.isFinite(range.max) || range.max <= range.min) return
      zoomMin.value = range.min; zoomMax.value = range.max
      zoomStep.value = Number.isFinite(range.step) && range.step > 0 ? range.step : .1
      const current = track.getSettings?.().zoom
      zoom.value = Math.max(range.min, Math.min(range.max, Number.isFinite(current) ? current : range.min))
      zoomSupported.value = true
    } catch { /* 能力读取失败不影响取景与快门。 */ }
  }
  async function setZoom(value) {
    const track = stream.value?.getVideoTracks?.()[0]
    if (!zoomSupported.value || zoomBusy.value || !track?.applyConstraints || !Number.isFinite(value)) return
    const token = generation
    const clamped = Math.max(zoomMin.value, Math.min(zoomMax.value, value))
    const target = Math.max(zoomMin.value, Math.min(zoomMax.value, zoomMin.value + Math.round((clamped - zoomMin.value) / zoomStep.value) * zoomStep.value))
    zoomBusy.value = true
    try {
      await track.applyConstraints({ advanced: [{ zoom: target }] })
      if (token !== generation) return
      const actual = track.getSettings?.().zoom
      zoom.value = Number.isFinite(actual) ? actual : target
    } catch {
      if (token === generation) {
        zoomSupported.value = false
        cameraNotice.value = '当前浏览器无法调整相机缩放，仍可正常取景和拍照。'
      }
    } finally { if (token === generation) zoomBusy.value = false }
  }
  let generation = 0
  function stop() {
    generation++
    stream.value?.getTracks().forEach(track => track.stop())
    stream.value = null
    zoomSupported.value = false; zoomBusy.value = false
  }
  async function start(requestedFacing = facingMode.value) {
    stop()
    const token = generation
    cameraNotice.value = ''
    if (!window.isSecureContext) throw new Error('请在 HTTPS 或 localhost 环境使用摄像头。')
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('当前浏览器不支持摄像头，请使用手机系统浏览器。')
    try {
      const options = mode => ({ video: { facingMode: { ideal: mode }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false })
      let next
      let selectedFacing = requestedFacing
      try { next = await navigator.mediaDevices.getUserMedia(options(requestedFacing)) }
      catch (error) {
        if (token !== generation || requestedFacing === facingMode.value || !['NotFoundError', 'OverconstrainedError', 'NotReadableError'].includes(error.name)) throw error
        selectedFacing = facingMode.value
        next = await navigator.mediaDevices.getUserMedia(options(selectedFacing))
        if (token === generation) cameraNotice.value = '无法切换到所选镜头，已恢复原镜头。'
      }
      // 权限弹窗期间可能已切换 Tab 或暂停，迟到的媒体流必须释放。
      if (token !== generation) {
        next.getTracks().forEach(track => track.stop())
        return null
      }
      stream.value = next
      const track = next.getVideoTracks?.()[0]
      let actualFacing
      try { actualFacing = track?.getSettings?.().facingMode } catch { /* 可选能力 */ }
      if (actualFacing && actualFacing !== requestedFacing) cameraNotice.value = '设备未提供所选镜头，继续使用当前可用镜头。'
      facingMode.value = ['user', 'environment'].includes(actualFacing) ? actualFacing : selectedFacing
      readControls(track)
      return next
    } catch (error) {
      if (token !== generation) return null
      const messages = {
        NotAllowedError: '摄像头权限未获允许，请在浏览器设置中允许访问后重试。',
        NotFoundError: '没有找到可用摄像头，请检查设备后重试。',
        NotReadableError: '摄像头可能被其他应用占用，请关闭其他相机应用后重试。',
        OverconstrainedError: '当前摄像头无法满足取景要求，请更换设备后重试。',
        SecurityError: '浏览器阻止了摄像头访问，请检查站点权限。',
      }
      throw new Error(messages[error.name] || '摄像头无法启动，请检查权限和设备后重试。')
    }
  }
  async function encodeFrame(video, maxEdge, quality, name) {
    if (!video.videoWidth || !video.videoHeight || video.readyState < 2) throw new Error('摄像头尚未就绪')
    const canvas = document.createElement('canvas')
    const scale = Math.min(1, maxEdge / Math.max(video.videoWidth, video.videoHeight))
    canvas.width = Math.max(1, Math.round(video.videoWidth * scale))
    canvas.height = Math.max(1, Math.round(video.videoHeight * scale))
    try {
      const context = canvas.getContext('2d')
      if (!context) throw new Error('浏览器无法处理摄像头画面。')
      context.drawImage(video, 0, 0, canvas.width, canvas.height)
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', quality))
      if (!blob || blob.type !== 'image/jpeg') throw new Error('抓帧失败，请重试')
      if (import.meta.env?.DEV) console.debug('[实时指导] capture', { width: canvas.width, height: canvas.height, bytes: blob.size })
      return new File([blob], name, { type: 'image/jpeg' })
    } finally { canvas.width = 0; canvas.height = 0 }
  }
  // 分析副本与用户照片明确分离，均直接从同一个 video 内容采样。
  const capture = video => encodeFrame(video, 640, .75, 'camera-fast.jpg')
  const capturePhoto = video => encodeFrame(video, Infinity, .92, `photo-${Date.now()}.jpg`)
  onUnmounted(stop)
  return { stream, start, stop, capture, capturePhoto, facingMode, cameraNotice, zoomSupported, zoom, zoomMin, zoomMax, zoomStep, zoomBusy, setZoom }
}
