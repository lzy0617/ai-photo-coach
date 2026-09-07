<script setup>
import ScoreCard from '../components/ScoreCard.vue'
import SuggestionCard from '../components/SuggestionCard.vue'
import AppIcon from '../components/AppIcon.vue'
defineProps({ result: Object, noPerson: Boolean, suggestions: Array })
const dimensions = [{ key: 'position', label: '主体位置' }, { key: 'headroom', label: '头顶留白' }, { key: 'subject_size', label: '主体大小' }]
const brightnessLabels = { dark: '偏暗', slightly_dark: '略暗', normal: '自然', slightly_bright: '略亮', bright: '偏亮' }
</script>
<template><div class="result-stack"><ScoreCard label="构图总分" :score="noPerson ? undefined : result?.composition?.score" :comment="noPerson ? '未检测到人物，暂不评分' : '由主体位置、头顶留白和主体大小综合评估'" large/><div class="dimension-cards"><ScoreCard v-for="item in dimensions" :key="item.key" :label="item.label" :score="noPerson ? undefined : result?.composition?.[item.key]?.score" :comment="noPerson ? '请拍摄包含人物的照片' : result?.composition?.[item.key]?.comment"/></div><section class="card brightness-card"><div class="section-bar"><span><AppIcon name="sun"/>整体亮度</span><span class="pill">{{ result?.brightness?.status === 'error' ? '暂不可用' : brightnessLabels[result?.brightness?.tendency] || '等待分析' }}</span></div><p>{{ result?.brightness?.comment || '分析后展示画面的亮度状态。' }}</p><p class="small muted">亮度描述不计入构图分数；明暗也可以是你的创作选择。</p></section><SuggestionCard :suggestions="suggestions" :no-person="noPerson" :ready="!!result"/><section class="card deep-card"><span class="eyebrow">BEYOND COMPOSITION</span><h3><AppIcon name="spark"/>不止构图，更懂你的表达</h3><p>从光影、氛围到叙事，探索照片的更多可能。</p><button class="button primary" disabled>AI 深度点评 <span class="pill">即将支持</span></button><span class="small muted">云端多模态大模型 · 正在接入</span></section></div></template>
