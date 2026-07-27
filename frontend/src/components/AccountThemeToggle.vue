<template>
  <el-tooltip :content="tooltipText" placement="bottom">
    <el-button
      text
      circle
      class="account-theme-toggle"
      :class="{ 'is-saving': saving }"
      :aria-label="tooltipText"
      :aria-pressed="isDark"
      :disabled="saving"
      data-testid="account-theme-toggle"
      @click="toggleTheme"
    >
      <el-icon :size="iconSize">
        <Loading v-if="saving" class="saving-icon" />
        <Sunny v-else-if="isDark" />
        <Moon v-else />
      </el-icon>
    </el-button>
  </el-tooltip>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Moon, Sunny } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import type { ResolvedTheme } from '@/utils/theme'

withDefaults(defineProps<{
  iconSize?: number
}>(), {
  iconSize: 19,
})

const userStore = useUserStore()
const saving = ref(false)
const resolvedTheme = ref<ResolvedTheme>('light')
let themeObserver: MutationObserver | null = null

const isDark = computed(() => resolvedTheme.value === 'dark')
const tooltipText = computed(() => {
  if (saving.value) return '正在保存界面模式'
  return isDark.value ? '切换为日间模式' : '切换为夜间模式'
})

function syncResolvedTheme(): void {
  resolvedTheme.value = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

async function toggleTheme(): Promise<void> {
  if (saving.value) return
  const targetMode = isDark.value ? 'light' : 'dark'
  saving.value = true
  try {
    await userStore.savePreference({
      theme_mode: targetMode,
    })
    ElMessage.success(targetMode === 'dark' ? '已切换为夜间模式' : '已切换为日间模式')
  } catch {
    ElMessage.error('界面模式保存失败，已恢复原设置')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  syncResolvedTheme()
  themeObserver = new MutationObserver(syncResolvedTheme)
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  })
})

onBeforeUnmount(() => {
  themeObserver?.disconnect()
  themeObserver = null
})
</script>

<style lang="scss" scoped>
.account-theme-toggle {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  border-radius: 6px;
  color: var(--text-regular, #52605b);

  &:hover,
  &:focus-visible {
    color: var(--primary-color, #176b73);
    background: var(--primary-lighter, #edf7f6);
  }

  &.is-saving {
    cursor: wait;
  }
}

.saving-icon {
  animation: theme-toggle-spin 0.8s linear infinite;
}

@keyframes theme-toggle-spin {
  to { transform: rotate(360deg); }
}
</style>
