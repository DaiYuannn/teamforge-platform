<template>
  <div
    class="empty-state"
    :class="{ 'empty-state--compact': compact }"
    :style="{ '--empty-accent': accent }"
  >
    <div class="empty-icon" aria-hidden="true">
      <el-icon :size="iconSize">
        <component :is="icon" />
      </el-icon>
    </div>

    <p class="empty-text">{{ text }}</p>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    text?: string
    description?: string
    icon?: string
    iconSize?: number
    /** Retained so existing call sites do not break. */
    illustration?: boolean
    compact?: boolean
    accent?: string
  }>(),
  {
    text: '暂无数据',
    description: '',
    icon: 'DocumentRemove',
    iconSize: 30,
    illustration: false,
    compact: false,
    accent: '#176B73',
  }
)
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 180px;
  padding: 32px 20px;

  &.empty-state--compact {
    min-height: 132px;
    padding: 20px 12px;
  }
}

.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  color: var(--empty-accent);
  background: var(--color-surface-strong);
  border-radius: 50%;
}

.empty-text {
  margin-top: 14px;
  color: var(--color-text-regular);
  font-size: 14px;
  font-weight: 600;
}

.empty-description {
  max-width: 42ch;
  margin-top: 6px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
  text-align: center;
}

.empty-action {
  margin-top: 16px;
}
</style>
