<template>
  <div class="empty-state">
    <el-icon :size="iconSize" color="#c0c4cc" aria-hidden="true">
      <component :is="icon" />
    </el-icon>
    <p class="empty-text">{{ text }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 空状态组件
 * 在没有数据时展示友好的提示
 */
withDefaults(
  defineProps<{
    /** 提示文字 */
    text?: string
    /** 图标名称 */
    icon?: string
    /** 图标大小 */
    iconSize?: number
  }>(),
  {
    text: '暂无数据',
    icon: 'FolderOpened',
    iconSize: 60,
  }
)
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;

  .empty-text {
    margin-top: 16px;
    font-size: 14px;
    color: #909399;
  }

  .empty-action {
    margin-top: 16px;
  }
}
</style>
