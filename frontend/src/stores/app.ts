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
  /** 当前设备类型 */
  const device = ref<DeviceType>('pc')

  // ============================================
  // Actions
  // ============================================

  /** 切换侧边栏折叠状态 */
  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  /** 设置设备类型 */
  function setDevice(type: DeviceType): void {
    device.value = type
  }

  return {
    // State
    sidebarCollapsed,
    device,
    // Actions
    toggleSidebar,
    setDevice,
  }
})
