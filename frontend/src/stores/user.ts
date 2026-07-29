import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import * as usersApi from '@/api/users'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '@/api/request'
import type { LoginParams, User, UserPreferences, UserRole } from '@/types'
import type { UserPreferenceData } from '@/api/users'
import { useAppStore } from '@/stores/app'
import { setLocale } from '@/i18n'
import {
  applyPrimaryColor,
  normalizeThemePreference,
  normalizePrimaryColor,
  resetPrimaryColor,
  type PrimaryColor,
} from '@/utils/theme'

async function clearNotificationSession(): Promise<void> {
  const { useNotificationStore } = await import('@/stores/notification')
  const notificationStore = useNotificationStore()
  notificationStore.stopStream()
  notificationStore.clearState()
}

/**
 * 用户状态管理 Store
 * 管理登录态、用户信息、角色权限
 */
export const useUserStore = defineStore('user', () => {
  const DEFAULT_DASHBOARD_CARDS = ['signals', 'priority', 'delivery', 'business']
  const DASHBOARD_CARD_ALIASES: Record<string, string> = {
    stats: 'signals',
    tasks: 'priority',
    timeline: 'delivery',
    gantt: 'delivery',
    finance: 'business',
    competitions: 'business',
  }
  // ============================================
  // State
  // ============================================

  /** Access Token */
  const token = ref<string>(getAccessToken() || '')
  /** Refresh Token */
  const refreshToken = ref<string>(getRefreshToken() || '')
  /** 用户信息 */
  const userInfo = ref<User | null>(null)
  /** 用户角色 */
  const role = ref<UserRole | ''>('')

  // ============================================
  // Getters
  // ============================================

  /** 是否已登录 */
  const isLoggedIn = computed(() => !!token.value)
  /** 是否为系统管理员 */
  const isAdmin = computed(() => role.value === 'sys_admin')
  /** 是否为小团队唯一的全局操作老师 */
  const isTeacher = computed(() => role.value === 'teacher')
  /** 是否为项目负责人（老师或管理员均可担任） */
  const isProjectLeader = computed(() => role.value === 'teacher' || role.value === 'sys_admin')
  /** 当前账户主色调 */
  const primaryColor = computed<PrimaryColor>(() =>
    normalizePrimaryColor(userInfo.value?.preferences?.primary_color)
  )
  const preferences = computed(() => userInfo.value?.preferences)
  const itemsPerPage = computed<10 | 20 | 50>(() =>
    [10, 20, 50].includes(Number(preferences.value?.items_per_page))
      ? Number(preferences.value?.items_per_page) as 10 | 20 | 50
      : 20
  )
  const notificationSoundEnabled = computed(() => preferences.value?.notification_sound !== false)
  const dashboardCards = computed<string[]>(() => {
    const rawCards = preferences.value?.dashboard_layout?.cards
    if (!Array.isArray(rawCards) || rawCards.length === 0) return DEFAULT_DASHBOARD_CARDS
    const normalized = rawCards
      .map((item) => DASHBOARD_CARD_ALIASES[String(item)] || String(item))
      .filter((item, index, list) =>
        DEFAULT_DASHBOARD_CARDS.includes(item) && list.indexOf(item) === index
      )
    return normalized.length ? normalized : DEFAULT_DASHBOARD_CARDS
  })

  // ============================================
  // Actions
  // ============================================

  function normalizePreferences(
    value: Partial<UserPreferences> | Partial<UserPreferenceData> | undefined,
    colorOverride?: string,
  ): UserPreferences {
    const landing = value?.default_landing
    const allowedLanding = ['dashboard', 'projects', 'tasks', 'notifications'] as const
    const normalizedLanding = allowedLanding.includes(landing as typeof allowedLanding[number])
      ? landing as UserPreferences['default_landing']
      : 'dashboard'
    const pageSize = Number(value?.items_per_page)
    const themePreference = normalizeThemePreference(value)
    return {
      dashboard_layout: value?.dashboard_layout || {},
      default_landing: normalizedLanding,
      sidebar_collapsed: value?.sidebar_collapsed ?? false,
      notification_sound: value?.notification_sound ?? true,
      language: value?.language === 'en' ? 'en' : 'zh-CN',
      items_per_page: ([10, 20, 50].includes(pageSize) ? pageSize : 20) as 10 | 20 | 50,
      theme_color: value?.theme_color,
      primary_color: normalizePrimaryColor(colorOverride ?? value?.primary_color),
      ...themePreference,
      default_scope: value?.default_scope === 'team' ? 'team' : 'mine',
      sidebar_order: Array.isArray(value?.sidebar_order) ? value.sidebar_order.map(String) : [],
      favorite_routes: Array.isArray(value?.favorite_routes) ? value.favorite_routes.map(String) : [],
      saved_filters: value?.saved_filters && typeof value.saved_filters === 'object'
        ? value.saved_filters
        : {},
      notification_preferences: value?.notification_preferences
        && typeof value.notification_preferences === 'object'
        ? value.notification_preferences
        : {},
    }
  }

  function syncPrimaryColor(value: unknown): PrimaryColor {
    const color = applyPrimaryColor(value)
    if (userInfo.value) {
      userInfo.value = {
        ...userInfo.value,
        preferences: normalizePreferences(userInfo.value.preferences, color),
      }
    }
    return color
  }

  function setCurrentUser(user: User): User {
    const color = normalizePrimaryColor(user.preferences?.primary_color)
    const normalizedUser: User = {
      ...user,
      preferences: normalizePreferences(user.preferences, color),
    }
    userInfo.value = normalizedUser
    role.value = normalizedUser.global_role
    applyPrimaryColor(color)
    useAppStore().applyUserPreference(normalizedUser.preferences)
    setLocale(normalizedUser.preferences?.language)
    return normalizedUser
  }

  /** 登录 */
  async function login(params: LoginParams): Promise<void> {
    const result = await authApi.login(params)
    await clearNotificationSession()
    token.value = result.token.access
    refreshToken.value = result.token.refresh
    setCurrentUser(result.user)
    setTokens(result.token.access, result.token.refresh, params.remember_me === true)
  }

  /** 退出登录 */
  async function logout(): Promise<void> {
    await clearNotificationSession().catch(() => undefined)
    try {
      await authApi.logout()
    } catch {
      // 即使后端退出失败，也清除本地状态
    }
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    role.value = ''
    clearTokens()
    resetPrimaryColor()
    useAppStore().resetUserPreference()
  }

  /** 获取用户信息 */
  async function fetchProfile(): Promise<User> {
    const user = await authApi.getProfile()
    return setCurrentUser(user)
  }

  /** 更新用户信息 */
  async function updateProfile(data: Partial<User>): Promise<User> {
    const user = await authApi.updateProfile(data)
    return setCurrentUser(user)
  }

  /** 保存偏好，并让所有入口共享同一套主色预览、确认与回滚逻辑。 */
  async function savePreference(data: Partial<UserPreferenceData>): Promise<UserPreferenceData> {
    const previousColor = primaryColor.value
    const appStore = useAppStore()
    const previousThemePreference = {
      theme_mode: appStore.themeMode,
      schedule_start: appStore.scheduleStart,
      schedule_end: appStore.scheduleEnd,
    }
    const requestedValue = data.primary_color ?? data.theme_color
    const requestedColor = requestedValue === undefined
      ? undefined
      : normalizePrimaryColor(requestedValue)

    if (requestedColor) syncPrimaryColor(requestedColor)
    if (data.theme_mode !== undefined || data.schedule_start !== undefined || data.schedule_end !== undefined) {
      appStore.applyThemeSettings({
        ...previousThemePreference,
        theme_mode: data.theme_mode ?? previousThemePreference.theme_mode,
        schedule_start: data.schedule_start ?? previousThemePreference.schedule_start,
        schedule_end: data.schedule_end ?? previousThemePreference.schedule_end,
      })
    }

    try {
      const preference = await usersApi.updateUserPreference({
        ...data,
        ...(requestedColor ? { primary_color: requestedColor } : {}),
      })
      const savedColor = syncPrimaryColor(
        preference.primary_color ?? preference.theme_color ?? requestedColor ?? previousColor
      )
      if (userInfo.value) {
        const updatedUser: User = {
          ...userInfo.value,
          preferences: normalizePreferences(preference, savedColor),
        }
        userInfo.value = updatedUser
        useAppStore().applyUserPreference(updatedUser.preferences)
      }
      return { ...preference, primary_color: savedColor }
    } catch (error) {
      syncPrimaryColor(previousColor)
      appStore.applyThemeSettings(previousThemePreference)
      throw error
    }
  }

  /** 从本地存储恢复用户信息（页面刷新时调用） */
  function restoreFromStorage(): void {
    const accessToken = getAccessToken()
    if (accessToken) {
      token.value = accessToken
    } else {
      resetPrimaryColor()
      useAppStore().resetUserPreference()
    }
  }

  function defaultLandingPath(): string {
    if (userInfo.value?.membership_status === 'external') return '/projects'
    const landing = preferences.value?.default_landing || 'dashboard'
    const allowed = new Set(['dashboard', 'projects', 'tasks', 'notifications'])
    return `/${allowed.has(landing) ? landing : 'dashboard'}`
  }

  return {
    // State
    token,
    refreshToken,
    userInfo,
    role,
    // Getters
    isLoggedIn,
    isAdmin,
    isTeacher,
    isProjectLeader,
    primaryColor,
    preferences,
    itemsPerPage,
    notificationSoundEnabled,
    dashboardCards,
    // Actions
    login,
    logout,
    fetchProfile,
    updateProfile,
    syncPrimaryColor,
    savePreference,
    restoreFromStorage,
    defaultLandingPath,
  }
})
