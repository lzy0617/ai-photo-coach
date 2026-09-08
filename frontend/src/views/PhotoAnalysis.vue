<script setup>
import { computed, ref } from 'vue'
import { savePhoto } from '../utils/savePhoto'
import TechnicalInfo from '../components/TechnicalInfo.vue'
import ScoreCard from '../components/ScoreCard.vue'
import SuggestionCard from '../components/SuggestionCard.vue'
import AppIcon from '../components/AppIcon.vue'
import { brightnessPresentation, dimensionPresentation, REFERENCE_DESCRIPTION } from '../utils/presentation'
const props = defineProps({ file: Object, result: Object, noPerson: Boolean, multiplePersons: Boolean, suggestions: Array })
const saving = ref(false), saveMessage = ref('')
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
    <section class="card deep-card">
      <h3><AppIcon name="spark"/>AI 深度点评 <span class="pill">即将支持</span></h3>
      <p>结合光影、背景、姿态与画面语义，提供更完整的摄影建议。</p>
      <button class="button primary" disabled>AI 深度点评 <span class="pill">即将支持</span></button>
      <span class="small muted">云端多模态模型 · 正在接入</span>
    </section>
  </div>
</template>
