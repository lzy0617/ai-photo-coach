<script setup>
import { computed } from 'vue'
import SuggestionCard from '../components/SuggestionCard.vue'
import ImageUploader from '../components/ImageUploader.vue'
import AppIcon from '../components/AppIcon.vue'
import { guideStatus } from '../utils/presentation'
const props = defineProps({ result: Object, noPerson: Boolean, multiplePersons: Boolean, suggestions: Array, loading: Boolean, health: String })
defineEmits(['select'])
const status = computed(() => props.loading ? '分析中' : guideStatus(props.result, props.noPerson, props.multiplePersons))
</script>
<template>
  <div class="result-stack live-guide">
    <SuggestionCard :suggestions="suggestions" :no-person="noPerson" :multiple-persons="multiplePersons" :ready="!!result" :loading="loading" immediate/>
    <div class="guide-status" aria-live="polite">
      <span>构图状态：<strong>{{ status }}</strong></span>
      <span><AppIcon name="chip" :size="17"/>Edge {{ health === 'online' ? '在线' : health === 'checking' ? '连接中' : '未连接' }}</span>
      <span>NPU {{ Number.isFinite(result?.timing?.infer_ms) ? `${result.timing.infer_ms.toFixed(1)} ms` : '等待推理' }}</span>
    </div>
    <div class="guide-actions">
      <button class="button primary" disabled aria-describedby="camera-pending"><AppIcon name="camera"/>开启实时指导</button>
      <p id="camera-pending" class="upload-note">实时摄像头尚未启用，将在 HTTPS 部署与摄像头接入完成后开放。</p>
      <ImageUploader simulation :disabled="loading" @select="$emit('select', $event)"/>
    </div>
  </div>
</template>
