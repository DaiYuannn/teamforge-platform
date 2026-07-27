<template>
  <el-pagination ref="paginationRef" v-bind="$attrs" />
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUpdated, ref } from 'vue'

defineOptions({
  name: 'AccessiblePagination',
  inheritAttrs: false,
})

const paginationRef = ref<{ $el?: HTMLElement }>()

function labelPageSizeSelect(): void {
  const input = paginationRef.value?.$el?.querySelector<HTMLInputElement>(
    '.el-pagination__sizes input[role="combobox"]'
  )
  if (input && !input.getAttribute('aria-label')) {
    input.setAttribute('aria-label', '每页显示条数')
  }
}

onMounted(() => nextTick(labelPageSizeSelect))
onUpdated(() => nextTick(labelPageSizeSelect))
</script>
