<script setup>
import { computed, ref, watch } from 'vue'
import { savePhoto } from '../utils/savePhoto'
import { prepareFastImage } from '../utils/image'
import { requestDeepReview } from '../api/photography'
import TechnicalInfo from '../components/TechnicalInfo.vue'
import ScoreCard from '../components/ScoreCard.vue'
import SuggestionCard from '../components/SuggestionCard.vue'
import DeepAnalysisCard from '../components/DeepAnalysisCard.vue'
import AppIcon from '../components/AppIcon.vue'
import { brightnessPresentation, dimensionPresentation, REFERENCE_DESCRIPTION } from '../utils/presentation'
const props = defineProps({ file: Object, result: Object, noPerson: Boolean, multiplePersons: Boolean, suggestions: Array })
const saving = ref(false), saveMessage = ref('')
const deepLoading = ref(false), deepResult = ref(null), deepError = ref('')
let deepRevision = 0
async function saveOriginal() {
  if (saving.value) return
  saving.value = true; saveMessage.value = ''
  try { saveMessage.value = await savePhoto(props.file) }
  catch { saveMessage.value = '暂时无法保存照片，请重试。' }
  finally { saving.value = false }
}
const dimensions = [{ key: 'position', label: '主体位置' }, { key: 'headroom', label: '上方留白' }, { key: 'subject_size', label: '主体占比' }]
const items = computed(() => dimensions.map(item => ({ ...item, ...dimensionPresentation(item.key, props.noPerson ? null : props.result?.composition?.[item.key]) })))
const brightness = computed(() => brightnessPresentation(props.result?.brightness))
watch(() => props.file, () => {
  deepRevision++
  deepLoading.value = false; deepResult.value = null; deepError.value = ''
})
async function analyzeDeep() {
  if (!props.file || !props.result || deepLoading.value) return
  const revision = deepRevision
  deepLoading.value = true; deepError.value = ''
  try {
    // 快速分析副本是 JPEG，且与 YOLO metrics 保持同一画面比例。
    const image = await prepareFastImage(props.file)
    if (revision !== deepRevision) return
    const response = await requestDeepReview(image, props.result)
    if (revision !== deepRevision) return
    if (!response.success) { deepError.value = response.message || 'AI 深度分析暂时不可用'; return }
    deepResult.value = response.deep_analysis
  } catch (error) {
    if (revision === deepRevision) deepError.value = error.message || 'AI 深度分析暂时不可用'
  } finally {
    if (revision === deepRevision) deepLoading.value = false
  }
}
</script>
<template>
  <div class="result-stack">
    <div v-if="file" class="save-photo-actions">
      <button class="button secondary" :disabled="saving" @click="saveOriginal">{{ saving ? '正在下载原图…' : '保存照片' }}</button>
      <p class="small muted">下载原始照片到浏览器下载位置。</p>
      <p v-if="saveMessage" class="small muted" role="status">{{ saveMessage }}</p>
    </div>
    <ScoreCard label="构图参考分" :score="noPerson ? undefined : result?.composition?.score" :badge="multiplePersons ? '单人规则参考' : ''" :comment="noPerson ? '暂未检测到清晰人物，暂不提供构图参考分。' : REFERENCE_DESCRIPTION" large/>
    <div class="dimension-cards">
      <section v-for="item in items" :key="item.key" class="card dimension-card">
        <div class="section-bar"><h3>{{ item.label }}</h3><strong class="dimension-state">{{ noPerson ? '暂不可用' : item.state }}</strong></div>
        <p>{{ noPerson ? '人物清晰入镜后，可查看这一关系。' : item.comment }}</p>
      </section>
    </div>
    <section class="card brightness-card">
      <div class="section-bar"><h3><AppIcon name="sun"/>整体亮度</h3><span class="pill">{{ brightness.state }}</span></div>
      <p>{{ brightness.comment }}</p>
      <p v-if="brightness.notes.length">{{ brightness.notes.join('；') }}</p>
      <p class="small muted">明暗也可能是创作选择，亮度统计不计入构图参考分。</p>
    </section>
    <SuggestionCard :suggestions="suggestions" :no-person="noPerson" :multiple-persons="multiplePersons" :ready="!!result"/>
    <details v-if="result" class="card technical-details">
      <summary>详细数据 <span class="muted">几何规则参考</span></summary>
      <p class="small muted">以下为边缘端规则数值，不代表精确的摄影质量评价。</p>
      <dl v-if="!noPerson"><template v-for="item in dimensions" :key="item.key"><dt>{{ item.label }}</dt><dd>{{ Number.isFinite(result.composition?.[item.key]?.score) ? `${result.composition[item.key].score} / 100` : '暂无数据' }}</dd></template></dl>
      <TechnicalInfo :result="result"/>
    </details>
    <DeepAnalysisCard :result="deepResult" :loading="deepLoading" :error="deepError" :disabled="!file || !result" @analyze="analyzeDeep"/>
  </div>
</template>
