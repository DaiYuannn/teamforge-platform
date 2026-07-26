import { defineStore } from 'pinia'
import { ref } from 'vue'

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
  } | null): void {
    sidebarCollapsed.value = preference?.sidebar_collapsed ?? false
    itemsPerPage.value = [10, 20, 50].includes(Number(preference?.items_per_page))
      ? Number(preference?.items_per_page) as 10 | 20 | 50
      : 20
  }

  /** 退出或切换账户时清除上一账户留下的界面状态。 */
  function resetUserPreference(): void {
    sidebarCollapsed.value = false
    itemsPerPage.value = 20
  }

  /** 设置设备类型 */
  function setDevice(type: DeviceType): void {
    device.value = type
  }

  return {
    // State
    sidebarCollapsed,
    itemsPerPage,
    device,
    // Actions
    toggleSidebar,
    applyUserPreference,
    resetUserPreference,
    setDevice,
  }
})
