<script setup>
import { ref } from 'vue'
import CompositionOverlay from './CompositionOverlay.vue'
import AppIcon from './AppIcon.vue'
defineProps({ source: String, result: Object, loading: Boolean })
const grid = ref(true), boxes = ref(true)
</script>
<template>
  <section class="viewer-card">
    <div class="section-bar"><span class="eyebrow">PHOTO FRAME <span class="muted">/ 取景画面</span></span><span class="small muted">{{ source ? '原始比例' : '等待照片' }}</span></div>
    <div class="photo-stage" :aria-busy="loading">
      <div v-if="source" class="photo-frame"><img :src="source" alt="待分析的人像照片"/><CompositionOverlay :persons="result?.detection?.persons" :image="result?.image" :grid="grid" :boxes="boxes"/></div>
      <div v-else class="photo-empty"><div class="frame-corner tl"/><div class="frame-corner tr"/><div class="frame-corner bl"/><div class="frame-corner br"/><span class="empty-icon"><AppIcon name="camera" :size="38"/></span><h3>好照片，从好的构图开始</h3><p>拍摄或选择一张人像照片<br>让 AI 帮你找到更好的取景方式</p><span class="empty-tag">人物检测 · 构图分析 · 即时建议</span></div>
      <div v-if="loading" class="analyzing" role="status"><span class="spinner"/> 正在通过边缘端分析…</div>
    </div>
    <div class="viewer-tools"><button :aria-pressed="grid" @click="grid = !grid" :class="{ selected: grid }"><AppIcon name="grid" :size="17"/>三分线</button><button :aria-pressed="boxes" @click="boxes = !boxes" :class="{ selected: boxes }"><span class="bbox-icon"/>人物框</button><span class="small muted">{{ result ? `${result.detection.persons.length} 位人物` : '辅助构图' }}</span></div>
  </section>
</template>
