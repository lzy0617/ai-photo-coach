<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({ result: Object, loading: Boolean, error: String, disabled: Boolean, live: Boolean })
defineEmits(['analyze'])
const text = (...values) => [...new Set(values.flat().filter(value => typeof value === 'string' && value.trim()))].join(' · ')

const details = computed(() => {
  const result = props.result || {}
  const rows = [
    ['场景', result.scene?.description || result.scene?.type],
    ['光线', text(result.lighting?.type, result.lighting?.quality, result.lighting?.problem)],
    ['背景', text(result.background?.quality, result.background?.distractions || [])],
    ['姿态', text(result.pose?.quality, result.pose?.problems || [])],
    ['表达', result.visual_expression],
  ]
  return rows.filter(([, value]) => typeof value === 'string' && value.trim())
})

const suggestions = computed(() => Array.isArray(props.result?.suggestions)
  ? props.result.suggestions.filter(item => item && typeof item.action === 'string' && item.action.trim())
  : [])
</script>

<template>
  <section class="card deep-card" aria-live="polite" :aria-busy="loading">
    <h3><AppIcon name="spark"/>AI 深度建议 <span class="pill">Qwen3-VL</span></h3>
    <p class="deep-source">结合当前关键帧与最近一次 YOLO / CV 数据，分析背景、光线、姿态和画面表达。</p>
    <div v-if="loading" class="deep-loading" role="status"><span class="spinner"/>{{ live ? '正在进行 AI 深度分析，实时 YOLO 指导仍会继续…' : '正在进行 AI 深度分析，已有 YOLO / CV 结果仍会保留…' }}</div>
    <div v-else-if="error" class="deep-error" role="alert">{{ error }}</div>
    <template v-if="result">
      <dl v-if="details.length" class="deep-details"><template v-for="([label, value], index) in details" :key="index"><dt>{{ label }}</dt><dd>{{ value }}</dd></template></dl>
      <ol v-if="suggestions.length" class="deep-suggestions">
        <li v-for="(item, index) in suggestions" :key="index"><strong>{{ item.action }}</strong><span v-if="item.reason">{{ item.reason }}</span></li>
      </ol>
      <p v-if="!details.length && !suggestions.length" class="muted">本次没有可展示的深度建议，可以换一个画面后重试。</p>
    </template>
    <button class="button primary" :disabled="disabled || loading" @click="$emit('analyze')">
      <span v-if="loading" class="spinner button-spinner"/>
      {{ loading ? '正在分析…' : result ? '重新进行 AI 深度分析' : 'AI 深度分析' }}
    </button>
    <span class="small muted">按需调用云端模型，不会按摄像头帧率连续请求。</span>
  </section>
</template>
