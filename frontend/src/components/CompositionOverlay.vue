<script setup>
import { computed } from 'vue'
import { boxLabelAlignment, normalizedBox } from '../utils/overlay'
const props = defineProps({ persons: { type: Array, default: () => [] }, image: Object, grid: Boolean, boxes: Boolean })
const regions = computed(() => props.persons.map(person => {
  const box = normalizedBox(person, props.image)
  return { box, confidence: person.confidence, labelAlignment: boxLabelAlignment(box) }
}).filter(item => item.box))
</script>
<template>
  <div class="composition-overlay" aria-hidden="true">
    <template v-if="grid"><i v-for="n in 2" :key="'v'+n" class="grid-line vertical" :style="{ left: `${n * 100 / 3}%` }"/><i v-for="n in 2" :key="'h'+n" class="grid-line horizontal" :style="{ top: `${n * 100 / 3}%` }"/></template>
    <template v-if="boxes"><div v-for="(region, index) in regions" :key="index" class="person-box" :class="{ 'label-right': region.labelAlignment === 'right' }" :style="{ left: `${region.box.x1 * 100}%`, top: `${region.box.y1 * 100}%`, width: `${(region.box.x2-region.box.x1)*100}%`, height: `${(region.box.y2-region.box.y1)*100}%` }"><span class="box-label">人物 {{ index + 1 }}<template v-if="Number.isFinite(region.confidence)"> · {{ Math.round(region.confidence * 100) }}%</template></span><i class="center-point"/></div></template>
  </div>
</template>
