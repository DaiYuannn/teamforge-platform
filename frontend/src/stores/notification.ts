import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getNotifications, getUnreadCount, markAllAsRead as markAllAsReadApi, markAsRead as markAsReadApi } from '@/api/notifications'
import { getAccessToken, refreshAccessToken } from '@/api/request'
import { useUserStore } from '@/stores/user'
import type { Notification } from '@/types'

type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'offline'

interface NotificationStateEvent {
  all_read?: boolean
  is_read?: boolean
  notification_id?: number
  unread_count?: number
}

interface StreamClosedEvent {
  reason?: 'token_expired' | 'account_inactive' | string
}

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<Notification[]>([])
  const unreadCount = ref(0)
  const connectionStatus = ref<ConnectionStatus>('idle')
  const lastEventId = ref(0)
  let abortController: AbortController | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  let stoppedManually = false
  let sessionRevision = 0
  let streamGeneration = 0

  const hasUnread = computed(() => unreadCount.value > 0)
  const recentNotifications = computed(() => notifications.value.slice(0, 5))

  function addNotification(notification: Notification, announce = true): void {
    if (notifications.value.some((item) => item.id === notification.id)) return
    notifications.value.unshift(notification)
    notifications.value = notifications.value.slice(0, 20)
    lastEventId.value = Math.max(lastEventId.value, notification.id)
    if (!notification.is_read) {
      unreadCount.value++
    }
    if (announce) playNotificationSound()
  }

  async function markAsRead(id: number): Promise<void> {
    const revision = sessionRevision
    await markAsReadApi(id)
    if (revision !== sessionRevision) return
    const item = notifications.value.find((n) => n.id === id)
    if (item && !item.is_read) {
      item.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  async function markAllAsRead(): Promise<void> {
    const revision = sessionRevision
    await markAllAsReadApi()
    if (revision !== sessionRevision) return
    notifications.value.forEach((n) => {
      n.is_read = true
    })
    unreadCount.value = 0
  }

  async function hydrate(): Promise<void> {
    const revision = sessionRevision
    const [listResponse, countResponse] = await Promise.all([
      getNotifications({ page: 1, page_size: 20 }),
      getUnreadCount(),
    ])
    if (revision !== sessionRevision) return
    const list: Notification[] = Array.isArray(listResponse)
      ? listResponse
      : ((listResponse as any).results || [])
    notifications.value = list
    unreadCount.value = Number((countResponse as any).count || 0)
    lastEventId.value = Math.max(0, ...list.map((item) => item.id))
  }

  function clearState(): void {
    sessionRevision++
    notifications.value = []
    unreadCount.value = 0
    lastEventId.value = 0
  }

  function playNotificationSound(): void {
    if (!useUserStore().notificationSoundEnabled || typeof window === 'undefined') return
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
      if (!AudioContextClass) return
      const context = new AudioContextClass()
      const oscillator = context.createOscillator()
      const gain = context.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.setValueAtTime(740, context.currentTime)
      gain.gain.setValueAtTime(0.0001, context.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.015)
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.16)
      oscillator.connect(gain)
      gain.connect(context.destination)
      oscillator.start()
      oscillator.stop(context.currentTime + 0.17)
      oscillator.addEventListener('ended', () => void context.close())
    } catch {
      // 浏览器尚未获得音频播放权限时保持静默。
    }
  }

  function applyUnreadCount(value: unknown): boolean {
    const count = Number(value)
    if (!Number.isFinite(count) || count < 0) return false
    unreadCount.value = Math.floor(count)
    return true
  }

  function applyNotificationState(payload: NotificationStateEvent): void {
    if (payload.all_read) {
      notifications.value.forEach((notification) => {
        notification.is_read = true
      })
      if (!applyUnreadCount(payload.unread_count)) unreadCount.value = 0
      return
    }

    const notificationId = Number(payload.notification_id)
    const item = Number.isInteger(notificationId)
      ? notifications.value.find((notification) => notification.id === notificationId)
      : undefined
    const transitionedToRead = Boolean(item && !item.is_read && payload.is_read !== false)
    if (item && payload.is_read !== false) item.is_read = true
    if (!applyUnreadCount(payload.unread_count) && transitionedToRead) {
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  async function handleStreamClosed(
    payload: StreamClosedEvent,
    generation: number,
  ): Promise<void> {
    if (generation !== streamGeneration) return
    const revision = sessionRevision
    stopStream()

    if (payload.reason === 'token_expired') {
      const refreshedToken = await refreshAccessToken()
      if (refreshedToken && revision === sessionRevision) {
        await startStream()
        return
      }
    }

    if (revision !== sessionRevision) return
    await useUserStore().logout()
    const { default: router } = await import('@/router')
    await router.replace('/login')
  }

  function processEventBlock(block: string, generation: number): void {
    if (!block.trim()) return
    let eventType = 'message'
    let eventId = 0
    const dataLines: string[] = []
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) eventType = line.slice(6).trim()
      else if (line.startsWith('id:')) eventId = Number(line.slice(3).trim()) || 0
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
    }
    if (generation !== streamGeneration) return
    if (eventId) lastEventId.value = Math.max(lastEventId.value, eventId)
    if (dataLines.length === 0) return
    try {
      const payload = JSON.parse(dataLines.join('\n'))
      if (eventType === 'notification' && payload?.data?.id) {
        connectionStatus.value = 'connected'
        addNotification(payload.data as Notification)
      } else if (eventType === 'notification_state') {
        connectionStatus.value = 'connected'
        applyNotificationState(payload as NotificationStateEvent)
      } else if (eventType === 'heartbeat') {
        connectionStatus.value = 'connected'
        applyUnreadCount(payload?.unread_count)
      } else if (eventType === 'fallback') {
        connectionStatus.value = 'reconnecting'
        applyUnreadCount(payload?.unread_count)
        void hydrate().catch(() => undefined)
      } else if (eventType === 'stream_closed') {
        void handleStreamClosed(payload as StreamClosedEvent, generation).catch(() => undefined)
      }
    } catch {
      // 丢弃不完整或无法解析的单条消息，连接保持可用。
    }
  }

  function scheduleReconnect(): void {
    if (stoppedManually || reconnectTimer) return
    connectionStatus.value = typeof navigator === 'undefined' || navigator.onLine
      ? 'reconnecting'
      : 'offline'
    const delay = Math.min(30000, 1000 * 2 ** Math.min(reconnectAttempts, 5))
    reconnectAttempts++
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      void startStream()
    }, delay)
  }

  async function startStream(): Promise<void> {
    stopStream(false)
    const generation = streamGeneration
    const token = getAccessToken()
    if (!token) {
      connectionStatus.value = 'idle'
      return
    }
    stoppedManually = false
    const revision = sessionRevision
    abortController = new AbortController()
    connectionStatus.value = reconnectAttempts ? 'reconnecting' : 'connecting'
    const baseUrl = String(import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
    const url = `${baseUrl}/notifications/sse/?last_id=${lastEventId.value}`

    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}`, Accept: 'text/event-stream' },
        cache: 'no-store',
        signal: abortController.signal,
      })
      if (revision !== sessionRevision || generation !== streamGeneration) return
      if (response.status === 401) {
        const refreshedToken = await refreshAccessToken()
        if (refreshedToken && !stoppedManually) {
          void startStream()
          return
        }
      }
      if (!response.ok || !response.body) throw new Error(`SSE HTTP ${response.status}`)
      connectionStatus.value = 'connected'
      reconnectAttempts = 0
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        if (revision !== sessionRevision || generation !== streamGeneration) return
        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split(/\r?\n\r?\n/)
        buffer = blocks.pop() || ''
        blocks.forEach((block) => processEventBlock(block, generation))
      }
      if (!stoppedManually && generation === streamGeneration) scheduleReconnect()
    } catch (error) {
      if (
        !stoppedManually
        && generation === streamGeneration
        && (error as Error).name !== 'AbortError'
      ) scheduleReconnect()
    }
  }

  function stopStream(manual = true): void {
    streamGeneration++
    stoppedManually = manual
    abortController?.abort()
    abortController = null
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = null
    if (manual) connectionStatus.value = 'idle'
  }

  return {
    notifications,
    unreadCount,
    connectionStatus,
    lastEventId,
    hasUnread,
    recentNotifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    hydrate,
    clearState,
    startStream,
    stopStream,
  }
})
