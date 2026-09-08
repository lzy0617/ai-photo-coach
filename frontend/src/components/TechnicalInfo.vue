<script setup>
defineProps({ result: Object, roundTrip: Number })
const milliseconds = value => Number.isFinite(value) ? `${value.toFixed(1)} ms` : '暂无数据'
</script>
<template>
  <dl class="technical-values">
    <dt>设备</dt><dd>{{ result?.backend?.device || '暂无数据' }}</dd>
    <dt>加速器</dt><dd>{{ result?.backend?.accelerator || '暂无数据' }}</dd>
    <dt>检测模型</dt><dd>{{ result?.backend?.model || '暂无数据' }}</dd>
    <dt>NPU infer_ms</dt><dd>{{ milliseconds(result?.timing?.infer_ms) }}</dd>
    <dt>后端 total_ms</dt><dd>{{ milliseconds(result?.timing?.total_ms) }}</dd>
    <template v-if="Number.isFinite(roundTrip)"><dt>请求往返耗时</dt><dd>{{ milliseconds(roundTrip) }}</dd></template>
  </dl>
</template>
