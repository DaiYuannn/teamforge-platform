import { useNotificationStore } from '@/stores/notification'
import { computed } from 'vue'

/** 实时通知 Store 的轻量组合式封装。 */
export function useNotification() {
  const notificationStore = useNotificationStore()

  /** 未读通知数量 */
  const unreadCount = computed(() => notificationStore.unreadCount)
  /** 通知列表 */
  const notifications = computed(() => notificationStore.notifications)
  /** 是否有未读通知 */
  const hasUnread = computed(() => notificationStore.hasUnread)

  /** 标记通知为已读 */
  function markAsRead(id: number): void {
    notificationStore.markAsRead(id)
  }

  /** 全部标记已读 */
  function markAllAsRead(): void {
    notificationStore.markAllAsRead()
  }

  /** 清空通知 */
  function clearNotifications(): void {
    notificationStore.clearState()
  }

  return {
    unreadCount,
    notifications,
    hasUnread,
    markAsRead,
    markAllAsRead,
    clearNotifications,
  }
}
