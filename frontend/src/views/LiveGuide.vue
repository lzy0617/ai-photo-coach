<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { usePhotography } from '../composables/usePhotography'
import { initialStability, nextStability } from '../utils/liveStability'
import TechnicalInfo from '../components/TechnicalInfo.vue'
import ImageUploader from '../components/ImageUploader.vue'
import PhotoViewer from '../components/PhotoViewer.vue'
import CompositionOverlay from '../components/CompositionOverlay.vue'
import AppIcon from '../components/AppIcon.vue'
import { useCamera } from '../composables/useCamera'
import { analyzeFast } from '../api/photography'
import { liveAdvice, MULTI_PERSON_MESSAGE } from '../utils/presentation'
const props = defineProps({ busy: Boolean, health: String })
// 模拟照片属于此视图，复用上传逻辑但不读写照片诊断状态。
const { source, result, loading: simulationLoading, error: simulationError, selectFile, analyze } = usePhotography()
const loading = computed(() => simulationLoading.value || props.busy)
const stability = ref(initialStability())
const technicalResult = ref(null), roundTrip = ref(null)
const emit = defineEmits(['capture'])
const camera = useCamera()
const { zoomSupported, zoom, zoomMin, zoomMax, zoomStep, zoomBusy, cameraNotice } = camera
const takingPhoto = ref(false)
let framingRevision = 0
const video = ref(null), running = ref(false), starting = ref(false), analyzing = ref(false)
const liveResult = ref(null), liveMode = ref(false), cameraError = ref(''), networkError = ref('')
const grid = ref(true), boxes = ref(true), frameWidth = ref(3), frameHeight = ref(4)
const responseHealth = ref('')
let session = null
const displayedResult = computed(() => liveMode.value ? liveResult.value : result.value)
const noPerson = computed(() => !!displayedResult.value && (displayedResult.value.composition?.status === 'no_person' || !displayedResult.value.detection?.persons?.length))
const multiplePersons = computed(() => (displayedResult.value?.detection?.persons?.length ?? 0) > 1)
const advice = computed(() => liveMode.value ? (stability.value.stable ? '✓ 当前构图较稳定，可以拍摄' : liveAdvice(liveResult.value)) : result.value ? liveAdvice(result.value) : '开启摄像头，试着调整你的取景。')
const edge = computed(() => responseHealth.value || props.health)
const frameStyle = computed(() => ({ aspectRatio: `${frameWidth.value} / ${frameHeight.value}`, width: `min(100%, calc(var(--camera-frame-height) * ${frameWidth.value / frameHeight.value}))` }))
const hudAdvice = computed(() => cameraError.value || (networkError.value ? '正在等待分析服务' : noPerson.value || !liveResult.value ? '让人物进入画面' : advice.value))
const hudNote = computed(() => multiplePersons.value ? '多人场景 · 仅作单人规则位置参考' : takingPhoto.value ? '正在保存照片…' : starting.value ? '正在开启摄像头' : !running.value ? '已暂停' : analyzing.value ? '正在分析…' : '实时取景')
function resize() {
  if (!video.value?.videoWidth) return
  frameWidth.value = video.value.videoWidth
  frameHeight.value = video.value.videoHeight
  // 旋转设备后丢弃旧方向的检测框。
  liveResult.value = null; stability.value = initialStability()
}
function pause() {
  session?.abort()
  session = null
  running.value = false; starting.value = false; analyzing.value = false
  camera.stop()
  if (video.value) video.value.srcObject = null
  liveResult.value = null; stability.value = initialStability()
}
function sleep(ms, signal) {
  return new Promise(resolve => {
    const finish = () => { clearTimeout(timer); signal.removeEventListener('abort', finish); resolve() }
    const timer = setTimeout(finish, ms)
    signal.addEventListener('abort', finish, { once: true })
    if (signal.aborted) finish()
  })
}
async function loop(controller) {
  const { signal } = controller
  let failures = 0
  while (!signal.aborted) {
    let delay = 250
    // 等待视频首帧或旋转后的新帧，不发送空帧。
    if (!video.value || video.value.readyState < 2) { await sleep(250, signal); continue }
    const revision = framingRevision
    const width = video.value.videoWidth, height = video.value.videoHeight
    let image
    try { image = await camera.capture(video.value) }
    catch (error) {
      if (!signal.aborted) { pause(); cameraError.value = error.message }
      return
    }
    if (signal.aborted) break
    const started = performance.now()
    analyzing.value = true
    try {
      const result = await analyzeFast(image, { signal })
      if (signal.aborted) break
      // 旧帧与当前视频方向不同则不显示旧框，下一轮重新抓帧。
      if (revision === framingRevision && !zoomBusy.value && video.value.videoWidth === width && video.value.videoHeight === height) {
        liveResult.value = result
        stability.value = nextStability(stability.value, result)
        technicalResult.value = result
        roundTrip.value = performance.now() - started
      }
      responseHealth.value = 'online'; networkError.value = ''; failures = 0
      if (import.meta.env.DEV) console.debug('[实时指导] response', { roundTripMs: +(performance.now() - started).toFixed(1), backendTotalMs: result.timing?.total_ms })
    } catch {
      if (signal.aborted) break
      liveResult.value = null; stability.value = initialStability()
      responseHealth.value = 'offline'
      networkError.value = '分析服务暂时没有响应，正在等待下一次分析。'
      delay = Math.min(5000, 1000 * 2 ** Math.min(failures++, 3))
    } finally { if (session === controller) analyzing.value = false }
    await sleep(delay, signal)
  }
}
async function start(facing = camera.facingMode.value) {
  if (running.value || starting.value || loading.value) return
  const controller = new AbortController()
  session = controller
  starting.value = true; liveMode.value = true
  cameraError.value = ''; networkError.value = ''; responseHealth.value = ''; liveResult.value = null; stability.value = initialStability()
  try {
    const stream = await camera.start(facing)
    if (!stream || controller.signal.aborted) return
    await nextTick()
    if (controller.signal.aborted) return
    video.value.srcObject = stream
    await video.value.play()
    if (controller.signal.aborted) return
    resize()
    stream.getVideoTracks().forEach(track => track.addEventListener('ended', () => {
      if (session === controller) { pause(); cameraError.value = '摄像头连接已中断，可以重新开启指导。' }
    }, { once: true }))
    starting.value = false; running.value = true
    void loop(controller)
  } catch (error) {
    if (!controller.signal.aborted) { pause(); cameraError.value = error.message || '摄像头画面无法播放，请重试。' }
  }
}
async function takePhoto() {
  if (!running.value || takingPhoto.value || loading.value || zoomBusy.value) return
  const controller = session
  takingPhoto.value = true
  cameraError.value = ''
  try {
    const photo = await camera.capturePhoto(video.value)
    if (session !== controller || controller.signal.aborted) return
    pause()
    emit('capture', photo)
  } catch (error) {
    if (session === controller) cameraError.value = error.message || '拍摄失败，请重试。'
  } finally { takingPhoto.value = false }
}
async function switchCamera() {
  if (!running.value || takingPhoto.value || zoomBusy.value) return
  const nextFacing = camera.facingMode.value === 'environment' ? 'user' : 'environment'
  pause()
  await start(nextFacing)
}
async function changeZoom(value) {
  if (!running.value || zoomBusy.value || takingPhoto.value) return
  framingRevision++
  liveResult.value = null; stability.value = initialStability()
  await camera.setZoom(Number(value))
  framingRevision++
  liveResult.value = null; stability.value = initialStability()
}
function visibilityChange() { if (document.hidden) pause() }
function simulate(file) { liveMode.value = false; responseHealth.value = ''; cameraError.value = ''; networkError.value = ''; void selectFile(file) }
onMounted(() => document.addEventListener('visibilitychange', visibilityChange))
onUnmounted(() => { pause(); document.removeEventListener('visibilitychange', visibilityChange) })
</script>
<template>
  <div class="result-stack live-guide" :class="{ 'live-guide-active': liveMode }">
    <section v-if="liveMode" class="viewer-card camera-session">
      <div class="video-stage camera-viewport"><div class="video-frame" :style="frameStyle">
        <video ref="video" autoplay playsinline muted @resize="resize"/>
        <CompositionOverlay :persons="liveResult?.detection?.persons" :image="liveResult?.image" :grid="grid" :boxes="boxes && running"/>
        <p v-if="!running" class="camera-placeholder">{{ starting ? '请允许浏览器使用摄像头' : '已暂停' }}</p>
        <div class="camera-status-hud">
          <div class="camera-telemetry"><span :class="{ 'edge-connected': edge === 'online' }">● {{ edge === 'online' ? '分析服务在线' : '正在等待分析服务' }}</span><span>分析 {{ liveResult && Number.isFinite(roundTrip) ? `${(roundTrip / 1000).toFixed(1)} s` : '—' }}</span></div>
          <div class="camera-display-controls">
            <button :aria-pressed="grid" aria-label="显示三分线" title="三分线" @click="grid = !grid"><AppIcon name="grid" :size="18"/></button>
            <button :aria-pressed="boxes" aria-label="显示人物框" title="人物框" @click="boxes = !boxes"><span class="bbox-icon"/></button>
          </div>
        </div>
        <div class="live-advice-hud" aria-live="polite" :title="cameraError || networkError || (multiplePersons ? MULTI_PERSON_MESSAGE : hudAdvice)">
          <p class="hud-advice-text">{{ hudAdvice }}</p>
          <p class="hud-note">{{ hudNote }}</p>
        </div>
      </div></div>
      <div class="camera-controls">
        <div v-if="running && zoomSupported" class="zoom-controls">
          <button aria-label="缩小" :disabled="zoomBusy || takingPhoto || zoom <= zoomMin" @click="changeZoom(zoom - zoomStep)">−</button>
          <output aria-label="当前缩放倍率">{{ zoom.toFixed(1) }}×</output>
          <input type="range" aria-label="相机缩放" :min="zoomMin" :max="zoomMax" :step="zoomStep" :value="zoom" :disabled="zoomBusy || takingPhoto" @change="changeZoom($event.target.value)">
          <button aria-label="放大" :disabled="zoomBusy || takingPhoto || zoom >= zoomMax" @click="changeZoom(zoom + zoomStep)">＋</button>
        </div>
        <p v-else class="camera-control-note" :title="cameraNotice">{{ running ? (cameraNotice || '当前设备不支持网页缩放控制') : '准备好后，继续取景' }}</p>
        <div v-if="running" class="camera-action-row">
          <button class="camera-icon-button" :disabled="takingPhoto || zoomBusy" aria-label="切换镜头" title="切换镜头" @click="switchCamera"><span aria-hidden="true">↻</span><small>切镜头</small></button>
          <button class="shutter-button" :disabled="takingPhoto || loading || zoomBusy" aria-label="拍摄照片并进入照片诊断" @click="takePhoto"><span/></button>
          <button class="camera-icon-button" aria-label="暂停指导" title="暂停指导" @click="pause"><span aria-hidden="true">Ⅱ</span><small>暂停</small></button>
        </div>
        <div v-else class="camera-action-row camera-resume-row">
          <button v-if="starting" class="button secondary" @click="pause">取消开启</button>
          <button v-else class="button primary" :disabled="loading" @click="start()"><AppIcon name="camera"/>继续指导</button>
        </div>
      </div>
    </section>
    <template v-else>
      <PhotoViewer :source="source" :result="result" :loading="loading" guide/>
      <section class="live-advice" aria-live="polite"><h3>{{ advice }}</h3><p v-if="result" class="small muted">当前为单张照片模拟结果</p></section>
      <p v-if="multiplePersons" class="notice" role="status">{{ MULTI_PERSON_MESSAGE }}</p>
      <button class="button primary" :disabled="loading" @click="start()"><AppIcon name="camera"/>开启实时指导</button>
    </template>
    <div v-if="!running && !starting" class="guide-actions">
      <div v-if="cameraError" class="error-card" role="alert">{{ cameraError }}</div>
      <div v-if="simulationError" class="error-card" role="alert"><p>{{ simulationError }}</p><button v-if="source" class="button secondary" :disabled="loading" @click="analyze">重新分析照片</button></div>
      <details v-if="technicalResult" class="card technical-details"><summary>技术信息</summary><TechnicalInfo :result="technicalResult" :round-trip="roundTrip"/></details>
      <ImageUploader simulation :disabled="loading" @select="simulate"/>
    </div>
  </div>
</template>
