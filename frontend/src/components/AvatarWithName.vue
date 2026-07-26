<template>
  <div class="avatar-with-name" :style="{ gap: gap + 'px' }">
    <el-avatar
      :size="size"
      :src="resolvedAvatar || undefined"
      :class="['awn-avatar', { 'awn-avatar--img': hasAvatar }]"
      :style="!hasAvatar ? { background: bgColor, color: '#fff' } : undefined"
    >
      <span v-if="!hasAvatar" class="awn-initial">{{ initial }}</span>
    </el-avatar>
    <span v-if="showName && name" class="awn-name" :style="{ fontSize: nameFontSize + 'px' }">{{ name }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * 带姓名的头像组件（需求D）
 * - 有头像图片时显示 img
 * - 无头像时取姓名最后一个字，背景色基于姓名 hash 生成
 */
const props = withDefaults(
  defineProps<{
    /** 姓名 */
    name?: string
    /** 头像地址 */
    avatarUrl?: string | null
    /** 头像尺寸 */
    size?: number
    /** 是否显示姓名文字 */
    showName?: boolean
    /** 头像与姓名间距 */
    gap?: number
  }>(),
  {
    name: '',
    avatarUrl: '',
    size: 36,
    showName: true,
    gap: 8,
  }
)

// 是否存在有效头像
const hasAvatar = computed(() => !!resolvedAvatar.value)

// 解析头像地址（兼容相对路径）
const resolvedAvatar = computed(() => {
  const url = props.avatarUrl
  if (!url) return ''
  if (/^https?:\/\//i.test(url) || url.startsWith('data:') || url.startsWith('/')) return url
  // 相对路径补 / 前缀
  return '/' + url.replace(/^\/+/, '')
})

// 取姓名最后一个字（兼容中英文，去除空格）
const initial = computed(() => {
  const n = (props.name || '').trim()
  if (!n) return 'U'
  return n.charAt(n.length - 1)
})

// 姓名字号
const nameFontSize = computed(() => {
  if (props.size <= 28) return 12
  if (props.size <= 40) return 13
  return 14
})

// 基于姓名 hash 的柔和背景色
const bgColor = computed(() => pickColor(props.name))

/** 一组柔和的头像背景色（与 Element Plus 主色系协调） */
const PALETTE = [
  '#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#9B59B6',
  '#36CFC9', '#1890FF', '#52C41A', '#FA8C16', '#EB2F96',
  '#722ED1', '#13C2C2',
]

/** 根据姓名生成稳定的背景色 */
function pickColor(name: string): string {
  if (!name) return PALETTE[0]
  let h = 0
  for (let i = 0; i < name.length; i++) {
    h = (Math.imul(31, h) + name.charCodeAt(i)) | 0
  }
  return PALETTE[Math.abs(h) % PALETTE.length]
}
</script>

<style lang="scss" scoped>
.avatar-with-name {
  display: inline-flex;
  align-items: center;
  min-width: 0;

  .awn-avatar {
    flex-shrink: 0;
    font-weight: 600;
    user-select: none;

    .awn-initial {
      font-size: 14px;
      line-height: 1;
    }

    &.awn-avatar--img {
      :deep(img) {
        object-fit: cover;
      }
    }
  }

  .awn-name {
    color: var(--color-text);
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }
}
</style>
