<script setup>
import { ref } from 'vue'
import AppIcon from './AppIcon.vue'
defineProps({ disabled: Boolean, hasPhoto: Boolean })
const emit = defineEmits(['select'])
const camera = ref(null), gallery = ref(null)
function change(event) { const file = event.target.files?.[0]; if (file) emit('select', file); event.target.value = '' }
</script>
<template><div class="upload-actions"><input ref="camera" class="visually-hidden" tabindex="-1" type="file" accept="image/*" capture="environment" :disabled="disabled" @change="change" aria-label="拍摄照片"/><input ref="gallery" class="visually-hidden" tabindex="-1" type="file" accept="image/*" :disabled="disabled" @change="change" aria-label="选择照片"/><button class="button primary" :disabled="disabled" @click="camera.click()"><AppIcon name="camera"/>{{ hasPhoto ? '重新拍摄' : '拍摄照片' }}</button><button class="button secondary" :disabled="disabled" @click="gallery.click()"><AppIcon name="image"/>选择照片</button></div><p class="upload-note">支持浏览器可读取的图片 · 最大 20 MB</p></template>
