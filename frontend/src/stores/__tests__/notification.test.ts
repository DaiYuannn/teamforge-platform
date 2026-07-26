import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const {
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAllAsRead,
  getAccessToken,
  refreshAccessToken,
  userStore,
  routerReplace,
} = vi.hoisted(() => ({
  getNotifications: vi.fn(),
  getUnreadCount: vi.fn(),
  markAsRead: vi.fn(),
  markAllAsRead: vi.fn(),
  getAccessToken: vi.fn(() => 'access-token'),
  refreshAccessToken: vi.fn(),
  userStore: {
    notificationSoundEnabled: false,
    logout: vi.fn(async () => undefined),
  },
  routerReplace: vi.fn(async () => undefined),
}))

vi.mock('@/api/notifications', () => ({
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAllAsRead,
}))

vi.mock('@/api/request', () => ({
  getAccessToken,
  refreshAccessToken,
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => userStore,
}))

vi.mock('@/router', () => ({
  default: { replace: routerReplace },
}))

import { useNotificationStore } from '@/stores/notification'
import type { Notification } from '@/types'

function notification(id: number, isRead = false): Notification {
  return {
    id,
    recipient: 1,
    title: `通知 ${id}`,
    content: '实时消息',
    notification_type: 'system',
    priority: 'normal',
    is_read: isRead,
    created_at: '2026-07-26 09:00:00',
  }
}

function eventResponse(...events: Array<{ event: string; id?: number; data: unknown }>): Response {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      const body = events.map(({ event, id, data }) => [
        `event: ${event}`,
        ...(id ? [`id: ${id}`] : []),
        `data: ${JSON.stringify(data)}`,
        '',
        '',
      ].join('\n')).join('')
      controller.enqueue(encoder.encode(body))
      controller.close()
    },
  })
  return new Response(stream, { status: 200 })
}

describe('notification realtime store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    getNotifications.mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [notification(3)],
    })
    getUnreadCount.mockResolvedValue({ count: 1 })
    markAsRead.mockResolvedValue(undefined)
    markAllAsRead.mockResolvedValue(undefined)
    getAccessToken.mockReturnValue('access-token')
    refreshAccessToken.mockResolvedValue(null)
    userStore.notificationSoundEnabled = false
    userStore.logout.mockResolvedValue(undefined)
    routerReplace.mockResolvedValue(undefined)
  })

  it('hydrates recent notifications and unread count', async () => {
    const store = useNotificationStore()
    await store.hydrate()
    expect(store.notifications.map((item) => item.id)).toEqual([3])
    expect(store.unreadCount).toBe(1)
    expect(store.lastEventId).toBe(3)
  })

  it('deduplicates SSE notifications by id', () => {
    const store = useNotificationStore()
    store.addNotification(notification(8), false)
    store.addNotification(notification(8), false)
    expect(store.notifications).toHaveLength(1)
    expect(store.unreadCount).toBe(1)
  })

  it('discards an in-flight hydration after the account session is cleared', async () => {
    let resolveNotifications!: (value: {
      count: number
      next: null
      previous: null
      results: Notification[]
    }) => void
    getNotifications.mockReturnValueOnce(new Promise((resolve) => {
      resolveNotifications = resolve
    }))
    const store = useNotificationStore()

    const hydration = store.hydrate()
    store.clearState()
    resolveNotifications({
      count: 1,
      next: null,
      previous: null,
      results: [notification(21)],
    })
    await hydration

    expect(store.notifications).toEqual([])
    expect(store.unreadCount).toBe(0)
    expect(store.lastEventId).toBe(0)
  })

  it('keeps API and local read state synchronized', async () => {
    const store = useNotificationStore()
    store.addNotification(notification(9), false)
    await store.markAsRead(9)
    expect(markAsRead).toHaveBeenCalledWith(9)
    expect(store.notifications[0].is_read).toBe(true)
    expect(store.unreadCount).toBe(0)
  })

  it('applies single and all-read state broadcasts from another client', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(eventResponse(
      {
        event: 'notification_state',
        data: {
          type: 'notification_state',
          notification_id: 8,
          is_read: true,
          all_read: false,
          unread_count: 1,
        },
      },
      {
        event: 'notification_state',
        data: {
          type: 'notification_state',
          is_read: true,
          all_read: true,
          unread_count: 0,
        },
      },
    ))
    const store = useNotificationStore()
    store.addNotification(notification(8), false)
    store.addNotification(notification(9), false)

    await store.startStream()
    store.stopStream()

    expect(store.notifications.every((item) => item.is_read)).toBe(true)
    expect(store.unreadCount).toBe(0)
    fetchMock.mockRestore()
  })

  it('hydrates local state when the stream falls back to database polling', async () => {
    getNotifications.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [notification(11, true)],
    })
    getUnreadCount.mockResolvedValueOnce({ count: 0 })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(eventResponse({
      event: 'fallback',
      data: { type: 'fallback', unread_count: 0 },
    }))
    const store = useNotificationStore()
    store.addNotification(notification(11), false)

    await store.startStream()
    await vi.waitFor(() => expect(getNotifications).toHaveBeenCalledOnce())
    store.stopStream()

    expect(store.notifications[0].is_read).toBe(true)
    expect(store.unreadCount).toBe(0)
    fetchMock.mockRestore()
  })

  it('logs out and returns to login when the server closes an inactive account stream', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(eventResponse({
      event: 'stream_closed',
      data: { type: 'stream_closed', reason: 'account_inactive' },
    }))
    const store = useNotificationStore()

    await store.startStream()
    await vi.waitFor(() => {
      expect(userStore.logout).toHaveBeenCalledOnce()
      expect(routerReplace).toHaveBeenCalledWith('/login')
    })

    expect(store.connectionStatus).toBe('idle')
    fetchMock.mockRestore()
  })

  it('refreshes the token and opens a replacement stream after token expiry', async () => {
    refreshAccessToken.mockResolvedValueOnce('renewed-access-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(eventResponse({
        event: 'stream_closed',
        data: { type: 'stream_closed', reason: 'token_expired' },
      }))
      .mockResolvedValueOnce(eventResponse({
        event: 'connected',
        data: { type: 'connected' },
      }))
    const store = useNotificationStore()

    await store.startStream()
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    store.stopStream()

    expect(refreshAccessToken).toHaveBeenCalledOnce()
    expect(userStore.logout).not.toHaveBeenCalled()
    fetchMock.mockRestore()
  })

  it('opens an authenticated SSE stream and consumes a notification event', async () => {
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(
          'event: notification\nid: 12\ndata: '
          + JSON.stringify({ type: 'notification', data: notification(12) })
          + '\n\n',
        ))
        controller.close()
      },
    })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(stream, { status: 200 }),
    )
    const store = useNotificationStore()
    await store.startStream()
    store.stopStream()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/notifications/sse/?last_id=0'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer access-token' }),
      }),
    )
    expect(store.notifications[0].id).toBe(12)
    fetchMock.mockRestore()
  })
})
