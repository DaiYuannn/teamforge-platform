import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/** 通知项 */
export interface NotificationItem {
  id: number
  title: string
  content: string
  type: 'info' | 'success' | 'warning' | 'error'
  read: boolean
  created_at: string
}

/**
 * 通知状态管理 Store（架构预留）
 * 未来对接 WebSocket 或轮询接口实现实时通知
 */
export const useNotificationStore = defineStore('notification', () => {
  // ============================================
  // State
  // ============================================

  /** 通知列表 */
  const notifications = ref<NotificationItem[]>([])
  /** 未读通知数量 */
  const unreadCount = ref<number>(0)

  // ============================================
  // Getters
  // ============================================

  /** 是否有未读通知 */
  const hasUnread = computed(() => unreadCount.value > 0)

  // ============================================
  // Actions（架构预留，待后续实现）
  // ============================================

  /** 添加通知 */
  function addNotification(notification: NotificationItem): void {
    notifications.value.unshift(notification)
    if (!notification.read) {
      unreadCount.value++
    }
  }

  /** 标记通知为已读 */
  function markAsRead(id: number): void {
    const item = notifications.value.find((n) => n.id === id)
    if (item && !item.read) {
      item.read = true
      unreadCount.value--
    }
  }

  /** 全部标记已读 */
  function markAllAsRead(): void {
    notifications.value.forEach((n) => {
      n.read = true
    })
    unreadCount.value = 0
  }

  /** 清空通知 */
  function clearNotifications(): void {
    notifications.value = []
    unreadCount.value = 0
  }

  return {
    // State
    notifications,
    unreadCount,
    // Getters
    hasUnread,
    // Actions
    addNotification,
    markAsRead,
    markAllAsRead,
    clearNotifications,
  }
})
