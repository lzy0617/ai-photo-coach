<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { checkHealth } from './api/photography'
import { usePhotography } from './composables/usePhotography'
import { NO_PERSON_MESSAGE, MULTI_PERSON_MESSAGE } from './utils/presentation'
import PhotoViewer from './components/PhotoViewer.vue'
import ImageUploader from './components/ImageUploader.vue'
import AppIcon from './components/AppIcon.vue'
import LiveGuide from './views/LiveGuide.vue'
import PhotoAnalysis from './views/PhotoAnalysis.vue'
const tab = ref('guide'), health = ref('checking')
const { source, result, loading, error, noPerson, multiplePersons, suggestions, selectFile, analyze } = usePhotography()
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
  <main class="app-main"><section class="intro"><h1>发现更好的<span>人像构图。</span></h1><p>基于端云协同的智能人像摄影辅助系统</p></section>
    <nav class="tabs" aria-label="功能导航"><button v-for="item in [{ id: 'guide', label: '实时指导', icon: 'camera' }, { id: 'analysis', label: '照片诊断', icon: 'image' }]" :key="item.id" :class="{ active: tab === item.id }" :aria-current="tab === item.id ? 'page' : undefined" @click="tab = item.id"><AppIcon :name="item.icon"/>{{ item.label }}<span>{{ item.id === 'guide' ? '拍摄前 · 取景辅助' : '拍摄后 · 单张分析' }}</span></button></nav>
    <div class="workspace" :class="{ 'guide-workspace': tab === 'guide' }">
      <div class="input-column">
        <PhotoViewer :source="source" :result="result" :loading="loading" :guide="tab === 'guide'"/>
        <ImageUploader v-if="tab === 'analysis'" :disabled="loading" :has-photo="!!source" @select="selectFile"/>
        <div v-if="error" class="error-card" role="alert"><p>{{ error }}</p><button v-if="source" class="button secondary" :disabled="loading" @click="analyze">重新分析</button></div>
        <div v-if="multiplePersons" class="notice" role="status">{{ MULTI_PERSON_MESSAGE }}</div>
        <div v-else-if="noPerson" class="notice" role="status">{{ NO_PERSON_MESSAGE }}</div>
      </div>
      <LiveGuide v-if="tab === 'guide'" :result="result" :no-person="noPerson" :multiple-persons="multiplePersons" :suggestions="suggestions" :loading="loading" :health="health" @select="selectFile"/>
      <PhotoAnalysis v-else :result="result" :no-person="noPerson" :multiple-persons="multiplePersons" :suggestions="suggestions"/>
    </div>
    <footer><span class="footer-brand">AI PHOTO COACH</span><span>边缘端构图参考 <i>·</i> 云端点评待接入</span></footer>
  </main>
</template>
