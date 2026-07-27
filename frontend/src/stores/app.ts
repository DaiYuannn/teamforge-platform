import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ThemeMode } from '@/types'
import {
  DEFAULT_SCHEDULE_END,
  DEFAULT_SCHEDULE_START,
  DEFAULT_THEME_MODE,
  applyThemePreference as applyDocumentThemePreference,
  normalizeThemePreference,
  resetThemePreference,
  type ThemePreference,
} from '@/utils/theme'

export type DeviceType = 'pc' | 'mobile'

/**
 * 应用状态管理 Store
 * 管理侧边栏折叠状态、设备类型
 */
export const useAppStore = defineStore('app', () => {
  // ============================================
  // State
  // ============================================

  /** 侧边栏是否折叠 */
  const sidebarCollapsed = ref<boolean>(false)
  /** 当前账户设置的默认分页条数 */
  const itemsPerPage = ref<10 | 20 | 50>(20)
  /** 当前账户选择的主题策略及定时范围 */
  const themeMode = ref<ThemeMode>(DEFAULT_THEME_MODE)
  const scheduleStart = ref(DEFAULT_SCHEDULE_START)
  const scheduleEnd = ref(DEFAULT_SCHEDULE_END)
  /** 当前设备类型 */
  const device = ref<DeviceType>('pc')

  // ============================================
  // Actions
  // ============================================

  /** 切换侧边栏折叠状态 */
  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  /** 应用当前账户的界面行为偏好。 */
  function applyUserPreference(preference?: {
    sidebar_collapsed?: boolean
    items_per_page?: number
    theme_mode?: ThemeMode
    schedule_start?: string
    schedule_end?: string
  } | null): void {
    sidebarCollapsed.value = preference?.sidebar_collapsed ?? false
    itemsPerPage.value = [10, 20, 50].includes(Number(preference?.items_per_page))
      ? Number(preference?.items_per_page) as 10 | 20 | 50
      : 20
    applyThemeSettings(preference)
  }

  function applyThemeSettings(preference?: Partial<ThemePreference> | null): void {
    const normalized = normalizeThemePreference(preference)
    themeMode.value = normalized.theme_mode
    scheduleStart.value = normalized.schedule_start
    scheduleEnd.value = normalized.schedule_end
    applyDocumentThemePreference(normalized)
  }

  /** 退出或切换账户时清除上一账户留下的界面状态。 */
  function resetUserPreference(): void {
    sidebarCollapsed.value = false
    itemsPerPage.value = 20
    themeMode.value = DEFAULT_THEME_MODE
    scheduleStart.value = DEFAULT_SCHEDULE_START
    scheduleEnd.value = DEFAULT_SCHEDULE_END
    resetThemePreference()
  }

  /** 设置设备类型 */
  function setDevice(type: DeviceType): void {
    device.value = type
  }

  return {
    // State
    sidebarCollapsed,
    itemsPerPage,
    themeMode,
    scheduleStart,
    scheduleEnd,
    device,
    // Actions
    toggleSidebar,
    applyUserPreference,
    applyThemeSettings,
    resetUserPreference,
    setDevice,
  }
})
