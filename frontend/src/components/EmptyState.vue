<template>
  <div class="empty-state" :class="{ 'empty-state--compact': compact }">
    <!-- SVG 插图（默认） -->
    <div v-if="illustration" class="empty-illustration" aria-hidden="true">
      <svg
        viewBox="0 0 200 140"
        xmlns="http://www.w3.org/2000/svg"
        :width="iconSize * 2.4"
        :height="iconSize * 1.68"
      >
        <defs>
          <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#ECF5FF" />
            <stop offset="100%" stop-color="#F5F7FA" />
          </linearGradient>
          <linearGradient :id="iconGradientId" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" :stop-color="accentColor" />
            <stop offset="100%" :stop-color="accentColorLight" />
          </linearGradient>
        </defs>
        <!-- 底部投影椭圆 -->
        <ellipse cx="100" cy="128" rx="64" ry="8" fill="#E6E8EB" opacity="0.6" />
        <!-- 空盒子 -->
        <path
          d="M70 56 L100 42 L130 56 L130 96 L100 110 L70 96 Z"
          fill="url(#gradientId)"
          stroke="#DCDFE6"
          stroke-width="1.5"
        />
        <path d="M70 56 L100 70 L130 56" fill="none" stroke="#C0C4CC" stroke-width="1.5" />
        <path d="M100 70 L100 110" fill="none" stroke="#DCDFE6" stroke-width="1.5" />
        <!-- 盖子（打开） -->
        <path
          d="M70 56 L100 42 L130 56 L100 70 Z"
          fill="url(#iconGradientId)"
          opacity="0.85"
        />
        <!-- 漂浮元素 -->
        <circle cx="58" cy="48" r="4" :fill="accentColor" opacity="0.5" />
        <circle cx="146" cy="64" r="3" :fill="accentColorLight" opacity="0.6" />
        <rect x="142" y="40" width="6" height="6" rx="1.5" :fill="accentColor" opacity="0.4" transform="rotate(20 145 43)" />
      </svg>
    </div>
    <!-- 图标模式 -->
    <div v-else class="empty-icon" :style="{ color: accentColor }">
      <el-icon :size="iconSize" aria-hidden="true">
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
import { computed } from 'vue'

/**
 * 空状态组件
 * 在没有数据时展示友好的提示，支持 SVG 插图、自定义图标、描述与操作按钮
 */
const props = withDefaults(
  defineProps<{
    /** 提示文字（主标题） */
    text?: string
    /** 补充描述（副标题） */
    description?: string
    /** 图标名称（Element Plus icon 名称，仅在 illustration=false 时使用） */
    icon?: string
    /** 图标大小 */
    iconSize?: number
    /** 是否使用 SVG 插图（默认 true） */
    illustration?: boolean
    /** 紧凑模式（减小内边距） */
    compact?: boolean
    /** 主题色（十六进制），用于插画与图标着色 */
    accent?: string
  }>(),
  {
    text: '暂无数据',
    description: '',
    icon: 'FolderOpened',
    iconSize: 56,
    illustration: true,
    compact: false,
    accent: '#409EFF',
  }
)

// 主题色与浅色变体
const accentColor = computed(() => props.accent)
const accentColorLight = computed(() => lighten(props.accent, 0.3))

// 唯一 gradient id，避免多实例冲突
const gradientId = computed(() => `es-grad-${Math.abs(hashCode(props.accent + props.icon))}`)
const iconGradientId = computed(() => `es-igrad-${Math.abs(hashCode(props.accent + props.icon))}`)

/** 简单字符串哈希 */
function hashCode(str: string): number {
  let h = 0
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0
  }
  return h
}

/** 将十六进制颜色按比例调亮 */
function lighten(hex: string, amount: number): string {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex.trim())
  if (!m) return hex
  const r = Math.min(255, Math.round(parseInt(m[1], 16) + 255 * amount))
  const g = Math.min(255, Math.round(parseInt(m[2], 16) + 255 * amount))
  const b = Math.min(255, Math.round(parseInt(m[3], 16) + 255 * amount))
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`
}
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;

  &.empty-state--compact {
    padding: 20px 12px;
  }

  .empty-illustration {
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
  }

  .empty-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.85;
  }

  .empty-text {
    margin-top: 16px;
    font-size: 14px;
    color: #606266;
    font-weight: 500;
  }

  .empty-description {
    margin-top: 6px;
    font-size: 12px;
    color: #909399;
  }

  .empty-action {
    margin-top: 16px;
  }
}
</style>
