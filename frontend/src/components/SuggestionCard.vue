<script setup>
import AppIcon from './AppIcon.vue'
import { NO_PERSON_MESSAGE } from '../utils/presentation'
defineProps({ suggestions: { type: Array, default: () => [] }, immediate: Boolean, noPerson: Boolean, multiplePersons: Boolean, ready: Boolean, loading: Boolean })
</script>
<template>
  <section class="suggestion-card" aria-live="polite">
    <div class="suggestion-heading"><AppIcon name="spark"/><span>{{ immediate ? '即时动作建议' : '摄影建议' }}</span></div>
    <template v-if="immediate">
      <h3>{{ loading ? '正在查看画面中的构图关系…' : noPerson ? NO_PERSON_MESSAGE : suggestions[0] || (ready ? '可以结合拍摄意图，观察人物与画面的关系。' : '选择一张照片，模拟一次取景指导。') }}</h3>
      <p>{{ multiplePersons ? '仅供所选主体的位置参考，可结合其他人物关系判断。' : ready ? '本次为单张照片模拟结果，调整取景后可再次选择照片。' : '实时取景尚未启用；当前可先体验单次建议。' }}</p>
    </template>
    <ol v-else-if="suggestions.length"><li v-for="(tip, index) in suggestions" :key="index"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ tip }}</li></ol>
    <p v-else>{{ ready ? '可以结合拍摄意图，继续关注人物、背景与光线的关系。' : '选择照片后，查看可尝试的构图调整。' }}</p>
  </section>
</template>
