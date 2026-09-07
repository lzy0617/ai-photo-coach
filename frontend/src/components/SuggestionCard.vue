<script setup>
import AppIcon from './AppIcon.vue'
defineProps({ suggestions: { type: Array, default: () => [] }, immediate: Boolean, noPerson: Boolean, ready: Boolean })
</script>
<template><section class="suggestion-card" aria-live="polite"><div class="suggestion-heading"><AppIcon name="spark"/><span>{{ immediate ? '此刻，试着这样拍' : '给你的摄影建议' }}</span><span class="small">{{ immediate ? 'QUICK TIP' : 'PHOTO TIPS' }}</span></div><template v-if="immediate"><h3>{{ noPerson ? '还没有找到人物主体' : suggestions[0] || (ready ? '当前构图较稳定' : '把人物放进画面，开始探索') }}</h3><p>{{ noPerson ? '让人物清晰入镜，再试一次。' : ready ? '调整取景后再次拍摄，看看构图的变化。' : '上传照片后，这里会出现一条即时构图建议。' }}</p></template><ol v-else-if="suggestions.length"><li v-for="(tip, index) in suggestions" :key="index"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ tip }}</li></ol><p v-else>{{ ready ? '当前基础构图较稳定，可以进一步关注背景与光线。' : '完成照片分析后，查看可执行的摄影建议。' }}</p></section></template>
