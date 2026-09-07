<script setup>
import { computed } from 'vue'
const props = defineProps({ label: String, score: Number, comment: String, large: Boolean, badge: String })
const value = computed(() => Number.isFinite(props.score) ? Math.round(Math.max(0, Math.min(100, props.score))) : null)
</script>
<template><section class="card score-card" :class="{ 'score-large': large }"><div class="score-top"><span>{{ label }}</span><span v-if="badge" class="pill score-badge">{{ badge }}</span><span class="score-number">{{ value ?? '—' }}<small v-if="value !== null"> / 100</small></span></div><div v-if="!large" class="progress" role="meter" :aria-label="label" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="value ?? undefined" :aria-valuetext="value === null ? '暂无评分' : `${value} 分`"><span :style="{ width: `${value ?? 0}%` }"/></div><p class="small muted">{{ comment || '分析后显示' }}</p></section></template>
