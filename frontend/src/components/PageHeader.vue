<template>
  <div class="page-header">
    <div class="header-content">
      <h2 class="header-title">{{ title }}</h2>
      <p v-if="subtitle" class="header-subtitle">{{ subtitle }}</p>
    </div>
    <div class="header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 页面头部组件
 * 显示页面标题、副标题和操作按钮区域
 */
withDefaults(
  defineProps<{
    /** 页面标题 */
    title: string
    /** 副标题 */
    subtitle?: string
  }>(),
  {
    subtitle: '',
  }
)
</script>

<style lang="scss" scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;

  .header-content {
    .header-title {
      font-size: 20px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }

    .header-subtitle {
      font-size: 13px;
      color: #909399;
      margin-top: 4px;
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

@media screen and (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;

    .header-actions {
      width: 100%;
    }
  }
}
</style>
