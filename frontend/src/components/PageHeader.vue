<template>
  <header class="page-header">
    <div class="header-content">
      <h1 class="header-title">{{ title }}</h1>
      <p v-if="subtitle" class="header-subtitle">{{ subtitle }}</p>
      <slot name="meta" />
    </div>
    <div class="header-actions">
      <slot name="actions" />
    </div>
  </header>
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 2px 0 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--color-border-light);

  .header-content {
    min-width: 0;

    .header-title {
      margin: 0;
      color: var(--color-text);
      font-size: 24px;
      font-weight: 600;
      line-height: 1.35;
      letter-spacing: 0;
    }

    .header-subtitle {
      max-width: 70ch;
      margin-top: 5px;
      color: var(--color-text-muted);
      font-size: 13px;
      line-height: 1.55;
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 0 0 auto;
    flex-wrap: wrap;
    justify-content: flex-end;

    &:empty {
      display: none;
    }
  }
}

@media screen and (max-width: 768px) {
  .page-header {
    gap: 12px;
    padding-bottom: 14px;
    margin-bottom: 14px;

    .header-content .header-title {
      font-size: 20px;
    }

    .header-actions {
      max-width: 48%;
    }
  }
}

@media screen and (max-width: 420px) {
  .page-header {
    flex-direction: column;

    .header-actions {
      width: 100%;
      max-width: none;
      justify-content: flex-start;
    }
  }
}
</style>
