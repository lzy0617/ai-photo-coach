<script setup>
import ScoreCard from '../components/ScoreCard.vue'
import SuggestionCard from '../components/SuggestionCard.vue'
import AppIcon from '../components/AppIcon.vue'
defineProps({ result: Object, noPerson: Boolean, suggestions: Array })
</script>
<template><div class="result-stack"><SuggestionCard :suggestions="suggestions" :no-person="noPerson" :ready="!!result" immediate/><div class="metrics-pair"><ScoreCard label="构图评分" :score="noPerson ? undefined : result?.composition?.score" :comment="noPerson ? '未检测到人物，暂不评分' : result ? '基于人物位置、留白与占比' : '等待第一张照片'" large/><section class="card timing-card"><span>NPU 推理耗时</span><div class="timing-number">{{ Number.isFinite(result?.timing?.infer_ms) ? result.timing.infer_ms.toFixed(2) : '—' }} <small>ms</small></div><p class="small muted"><AppIcon name="chip" :size="14"/> Ascend 边缘计算</p></section></div><section class="card realtime-card"><div><AppIcon name="camera"/><strong>让指导跟上你的镜头</strong></div><p>实时取景与连续构图建议，即将到来。</p><button class="button secondary" disabled>开始实时指导 <span class="pill">即将支持</span></button></section><p class="footnote">每一种构图都有可能。AI 建议，是创作的起点。</p></div></template>
