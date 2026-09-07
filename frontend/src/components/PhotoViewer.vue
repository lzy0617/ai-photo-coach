<script setup>
import { ref } from 'vue'
import CompositionOverlay from './CompositionOverlay.vue'
import AppIcon from './AppIcon.vue'
defineProps({ source: String, result: Object, loading: Boolean, guide: Boolean })
const grid = ref(true), boxes = ref(true)
</script>
<template>
  <section class="viewer-card">
    <div class="section-bar"><span class="viewer-title">{{ guide ? '实时取景' : '照片预览' }}</span><span class="small muted">{{ guide ? (source ? '照片模拟 · 非实时画面' : '摄像头未启用') : (source ? '原始比例' : '等待照片') }}</span></div>
    <div class="photo-stage" :aria-busy="loading">
      <div v-if="source" class="photo-frame"><img :src="source" alt="待分析的人像照片"/><CompositionOverlay :persons="result?.detection?.persons" :image="result?.image" :grid="grid" :boxes="boxes"/></div>
      <div v-else class="photo-empty"><div class="frame-corner tl"/><div class="frame-corner tr"/><div class="frame-corner bl"/><div class="frame-corner br"/><span class="empty-icon"><AppIcon name="camera" :size="38"/></span><h3>{{ guide ? '为下一次快门，调整取景' : '看一看这张照片的构图关系' }}</h3><p>{{ guide ? '实时画面与即时动作建议将在后续开放。' : '拍摄或选择一张照片，查看几何构图参考。' }}<br>{{ guide ? '现在可以选择照片，模拟一次指导。' : '人物位置、上方留白与亮度，一起看看。' }}</p></div>
      <div v-if="loading" class="analyzing" role="status"><span class="spinner"/> 正在通过边缘端分析…</div>
    </div>
    <div class="viewer-tools"><button :aria-pressed="grid" @click="grid = !grid" :class="{ selected: grid }"><AppIcon name="grid" :size="17"/>三分线</button><button :aria-pressed="boxes" @click="boxes = !boxes" :class="{ selected: boxes }"><span class="bbox-icon"/>人物框</button><span class="small muted">{{ result ? `${result.detection.persons.length} 位人物` : '辅助构图' }}</span></div>
  </section>
</template>
