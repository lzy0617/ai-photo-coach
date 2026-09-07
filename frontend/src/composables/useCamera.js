import { onUnmounted, ref } from 'vue'
// 为后续伪实时指导预留：start → video.srcObject → capture → analyzeFast。
// 当前 UI 不启用实时功能，不主动申请摄像头权限。
export function useCamera() {
  const stream = ref(null)
  function stop() { stream.value?.getTracks().forEach(track => track.stop()); stream.value = null }
  async function start() {
    stop()
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('请在 HTTPS 或 localhost 环境使用摄像头。')
    stream.value = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
    return stream.value
  }
  async function capture(video) {
    if (!video.videoWidth) throw new Error('摄像头尚未就绪')
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth; canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9))
    if (!blob) throw new Error('拍摄失败，请重试')
    return new File([blob], 'camera.jpg', { type: 'image/jpeg' })
  }
  onUnmounted(stop)
  return { stream, start, stop, capture }
}
