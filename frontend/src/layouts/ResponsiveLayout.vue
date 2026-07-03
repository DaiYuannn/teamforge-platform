<template>
  <PCLayout v-if="!isMobile" />
  <MobileLayout v-else />
</template>

<script setup lang="ts">
/**
 * 响应式布局组件
 * 根据窗口宽度自动切换 PCLayout / MobileLayout
 * 断点：768px（与 useDevice 默认值一致）
 */
import { useDevice } from '@/composables/useDevice'
import PCLayout from '@/layouts/PCLayout.vue'
import MobileLayout from '@/layouts/MobileLayout.vue'

const { isMobile } = useDevice()
</script>
