import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// Mock the request module so the store initializes without any persisted
// tokens and so that axios / element-plus are not loaded during the test.
vi.mock('@/api/request', () => ({
  getAccessToken: vi.fn(() => null),
  getRefreshToken: vi.fn(() => null),
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
}))

// Mock the auth API module to avoid any real network calls.
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

import { useUserStore } from '@/stores/user'

describe('useUserStore', () => {
  beforeEach(() => {
    // Provide a fresh pinia instance for every test so state does not leak.
    setActivePinia(createPinia())
  })

  it('initializes with empty state (token empty, userInfo null)', () => {
    const store = useUserStore()

    expect(store.token).toBe('')
    expect(store.refreshToken).toBe('')
    expect(store.userInfo).toBeNull()
    expect(store.role).toBe('')
  })

  it('reports not logged in when initialized without a token', () => {
    const store = useUserStore()

    expect(store.isLoggedIn).toBe(false)
    expect(store.isAdmin).toBe(false)
    expect(store.isTeacher).toBe(false)
    expect(store.isProjectLeader).toBe(false)
  })

  it('clears all state after logout', async () => {
    const store = useUserStore()

    // Simulate a previously logged-in user.
    store.token = 'fake-access-token'
    store.refreshToken = 'fake-refresh-token'
    store.role = 'member'
    store.userInfo = {
      id: 1,
      username: 'tester',
      email: 'tester@example.com',
      name: 'Tester',
      global_role: 'member',
      is_active: true,
      date_joined: '2024-01-01',
    }

    await store.logout()

    expect(store.token).toBe('')
    expect(store.refreshToken).toBe('')
    expect(store.userInfo).toBeNull()
    expect(store.role).toBe('')
    expect(store.isLoggedIn).toBe(false)
  })
})
