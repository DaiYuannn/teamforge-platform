import { afterEach, describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { notificationStore } = vi.hoisted(() => ({
  notificationStore: {
    stopStream: vi.fn(),
    clearState: vi.fn(),
  },
}))

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

vi.mock('@/api/users', () => ({
  updateUserPreference: vi.fn(),
}))

vi.mock('@/stores/notification', () => ({
  useNotificationStore: () => notificationStore,
}))

import * as authApi from '@/api/auth'
import * as usersApi from '@/api/users'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import {
  DEFAULT_PRIMARY_COLOR,
  DEFAULT_THEME_MODE,
  stopThemeRuntime,
} from '@/utils/theme'
import type { ThemeMode, User } from '@/types'

const userFixture = (
  primaryColor = '#176b73',
  themeMode: ThemeMode = 'system',
): User => ({
  id: 1,
  username: 'tester',
  email: 'tester@example.com',
  name: 'Tester',
  global_role: 'member',
  is_active: true,
  date_joined: '2024-01-01',
  preferences: {
    primary_color: primaryColor,
    theme_mode: themeMode,
    schedule_start: '19:00',
    schedule_end: '07:00',
    default_landing: 'dashboard',
    sidebar_collapsed: false,
    notification_sound: true,
    items_per_page: 20,
    dashboard_layout: {},
  },
})

describe('useUserStore', () => {
  beforeEach(() => {
    // Provide a fresh pinia instance for every test so state does not leak.
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.stubGlobal('matchMedia', vi.fn(() => ({
      matches: false,
      media: '(prefers-color-scheme: dark)',
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(() => true),
    })))
    document.documentElement.removeAttribute('style')
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.removeAttribute('data-theme-mode')
    document.documentElement.classList.remove('dark')
  })

  afterEach(() => {
    stopThemeRuntime()
    vi.unstubAllGlobals()
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
    store.userInfo = userFixture('#6f5a86')

    await store.logout()

    expect(store.token).toBe('')
    expect(store.refreshToken).toBe('')
    expect(store.userInfo).toBeNull()
    expect(store.role).toBe('')
    expect(store.isLoggedIn).toBe(false)
    expect(notificationStore.stopStream).toHaveBeenCalledOnce()
    expect(notificationStore.clearState).toHaveBeenCalledOnce()
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe(DEFAULT_PRIMARY_COLOR)
    expect(useAppStore().themeMode).toBe(DEFAULT_THEME_MODE)
    expect(document.documentElement.dataset.themeMode).toBe(DEFAULT_THEME_MODE)
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('applies the account primary color after login', async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      token: { access: 'access', refresh: 'refresh' },
      user: userFixture('#2f6f4e'),
    })
    const store = useUserStore()

    await store.login({ email: 'tester@example.com', password: 'secret123' })

    expect(notificationStore.stopStream).toHaveBeenCalledOnce()
    expect(notificationStore.clearState).toHaveBeenCalledOnce()
    expect(store.primaryColor).toBe('#2f6f4e')
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe('#2f6f4e')
  })

  it('applies the account dark theme after login', async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      token: { access: 'access', refresh: 'refresh' },
      user: userFixture('#2f6f4e', 'dark'),
    })
    const store = useUserStore()

    await store.login({ email: 'tester@example.com', password: 'secret123' })

    expect(useAppStore().themeMode).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(document.documentElement.dataset.themeMode).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('normalizes and stores the primary color returned by the profile endpoint', async () => {
    vi.mocked(authApi.getProfile).mockResolvedValue(userFixture('#6F5A86'))
    const store = useUserStore()

    await store.fetchProfile()

    expect(store.primaryColor).toBe('#6f5a86')
    expect(store.userInfo?.preferences?.primary_color).toBe('#6f5a86')
  })

  it('rolls back an optimistic primary color when saving fails', async () => {
    vi.mocked(authApi.getProfile).mockResolvedValue(userFixture('#176b73'))
    vi.mocked(usersApi.updateUserPreference).mockRejectedValue(new Error('save failed'))
    const store = useUserStore()
    await store.fetchProfile()

    await expect(store.savePreference({ primary_color: '#9a6238' })).rejects.toThrow('save failed')

    expect(store.primaryColor).toBe('#176b73')
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe('#176b73')
  })

  it('rolls back an optimistic theme when saving fails', async () => {
    vi.mocked(authApi.getProfile).mockResolvedValue(userFixture('#176b73', 'dark'))
    vi.mocked(usersApi.updateUserPreference).mockRejectedValue(new Error('save failed'))
    const store = useUserStore()
    await store.fetchProfile()

    await expect(store.savePreference({ theme_mode: 'light' })).rejects.toThrow('save failed')

    expect(useAppStore().themeMode).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(document.documentElement.dataset.themeMode).toBe('dark')
  })

  it('uses the project workspace as the safe landing page for an external account', () => {
    const store = useUserStore()
    store.userInfo = {
      ...userFixture(),
      membership_status: 'external',
    }

    expect(store.defaultLandingPath()).toBe('/projects')
  })
})
