import { computed, onUnmounted, ref } from 'vue'
import { analyzeFast } from '../api/photography'
import { prepareFastImage } from '../utils/image'
import { friendlyText, NO_PERSON_MESSAGE } from '../utils/presentation'
export function usePhotography() {
  const source = ref(''), file = ref(null), result = ref(null), loading = ref(false), error = ref('')
  let selection = 0
  // 单独缓存快速分析副本，失败重试无需再次压缩；file 始终保留原图。
  let fastFile = null
  const noPerson = computed(() => !!result.value && (result.value.composition.status === 'no_person' || !result.value.detection.persons.length))
  const multiplePersons = computed(() => (result.value?.detection?.persons?.length ?? 0) > 1)
  const suggestions = computed(() => {
    if (noPerson.value) return [NO_PERSON_MESSAGE]
    const items = result.value?.composition?.suggestions ?? result.value?.suggestions ?? []
    return Array.isArray(items) ? items.filter(item => typeof item === 'string').map(friendlyText) : []
  })
  async function analyze() {
    if (!file.value || loading.value) return
    loading.value = true; error.value = ''; result.value = null
    try {
      fastFile ??= await prepareFastImage(file.value)
      result.value = await analyzeFast(fastFile)
    }
    catch (e) { error.value = e.message }
    finally { loading.value = false }
  }
  async function selectFile(next) {
    if (!next || loading.value) return
    const token = ++selection
    error.value = ''
    if (!next.type.startsWith('image/')) { error.value = '请选择图片文件。'; return }
    if (next.size > 20 * 1024 * 1024) { error.value = '图片超过 20 MB，请选择较小的照片。'; return }
    const url = URL.createObjectURL(next)
    const image = new Image()
    image.src = url
    try { await image.decode() } catch {
      URL.revokeObjectURL(url)
      if (token === selection) error.value = '浏览器无法读取这张照片，请改用 JPG、PNG 或 WebP 格式。'
      return
    }
    if (token !== selection) { URL.revokeObjectURL(url); return }
    if (source.value) URL.revokeObjectURL(source.value)
    source.value = url; file.value = next; result.value = null
    fastFile = null
    await analyze()
  }
  onUnmounted(() => { selection++; if (source.value) URL.revokeObjectURL(source.value) })
  return { source, file, result, loading, error, noPerson, multiplePersons, suggestions, selectFile, analyze }
}
