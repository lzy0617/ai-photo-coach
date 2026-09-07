<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { checkHealth } from './api/photography'
import { usePhotography } from './composables/usePhotography'
import PhotoViewer from './components/PhotoViewer.vue'
import ImageUploader from './components/ImageUploader.vue'
import AppIcon from './components/AppIcon.vue'
import LiveGuide from './views/LiveGuide.vue'
import PhotoAnalysis from './views/PhotoAnalysis.vue'
const tab = ref('guide'), health = ref('checking')
const { source, result, loading, error, noPerson, suggestions, selectFile, analyze } = usePhotography()
let timer
async function refreshHealth() {
  if (health.value === 'checking' && timer) return
  health.value = 'checking'
  try { await checkHealth(); health.value = 'online' } catch { health.value = 'offline' }
}
onMounted(() => { refreshHealth(); timer = setInterval(refreshHealth, 30000) })
onUnmounted(() => clearInterval(timer))
</script>
<template>
  <header class="app-header"><div class="header-inner"><a class="brand" href="./" aria-label="AI Photo Coach 首页"><span class="brand-mark"><AppIcon name="camera" :size="25"/></span><span>AI Photo <strong>Coach</strong><small>让每一次快门，更有把握</small></span></a><button class="edge-status" :class="health" :disabled="health === 'checking'" @click="refreshHealth" title="点击重新检查 Edge 连接"><i/>{{ health === 'online' ? 'Edge 在线' : health === 'checking' ? '连接中' : 'Edge 未连接' }}<span v-if="health === 'offline'"> ↻</span></button></div></header>
  <main class="app-main"><section class="intro"><div class="eyebrow">YOUR PERSONAL PHOTO ASSISTANT</div><h1>发现更好的<span>人像构图。</span></h1><p>基于端云协同的智能人像摄影辅助系统</p></section>
    <nav class="tabs" aria-label="功能导航"><button v-for="item in [{ id: 'guide', label: '摄影指导', icon: 'camera' }, { id: 'analysis', label: '照片诊断', icon: 'image' }]" :key="item.id" :class="{ active: tab === item.id }" :aria-current="tab === item.id ? 'page' : undefined" @click="tab = item.id"><AppIcon :name="item.icon"/>{{ item.label }}<span>{{ item.id === 'guide' ? '捕捉好构图' : '读懂一张照片' }}</span></button></nav>
    <div class="workspace"><div class="input-column"><PhotoViewer :source="source" :result="result" :loading="loading"/><ImageUploader :disabled="loading" :has-photo="!!source" @select="selectFile"/><div v-if="error" class="error-card" role="alert"><p>{{ error }}</p><button v-if="source" class="button secondary" :disabled="loading" @click="analyze">重新分析</button></div><div v-if="noPerson" class="notice" role="status">未检测到人物主体。请让人物清晰入镜后重新拍摄。</div><div class="device-note"><AppIcon name="chip" :size="18"/><span>OrangePi AI Pro 20T <i>·</i> Ascend NPU <i>·</i> YOLOv5s</span></div></div><component :is="tab === 'guide' ? LiveGuide : PhotoAnalysis" :result="result" :no-person="noPerson" :suggestions="suggestions"/></div>
    <footer><span class="footer-brand">AI PHOTO COACH</span><span>边缘端快速分析 <i>＋</i> 云端深度理解</span></footer>
  </main>
</template>
