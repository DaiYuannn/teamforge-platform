import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '@/api/request'
import type { LoginParams, User, UserRole } from '@/types'

/**
 * 用户状态管理 Store
 * 管理登录态、用户信息、角色权限
 */
export const useUserStore = defineStore('user', () => {
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
  /** 是否为指导老师 */
  const isTeacher = computed(() => role.value === 'teacher')
  /** 是否为项目负责人（老师或管理员均可担任） */
  const isProjectLeader = computed(() => role.value === 'teacher' || role.value === 'sys_admin')

  // ============================================
  // Actions
  // ============================================

  /** 登录 */
  async function login(params: LoginParams): Promise<void> {
    const result = await authApi.login(params)
    token.value = result.token.access
    refreshToken.value = result.token.refresh
    userInfo.value = result.user
    role.value = (result.user as any).global_role || result.user.role
    setTokens(result.token.access, result.token.refresh)
  }

  /** 退出登录 */
  async function logout(): Promise<void> {
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
  }

  /** 获取用户信息 */
  async function fetchProfile(): Promise<User> {
    const user = await authApi.getProfile()
    userInfo.value = user
    role.value = (user as any).global_role || user.role
    return user
  }

  /** 更新用户信息 */
  async function updateProfile(data: Partial<User>): Promise<User> {
    const user = await authApi.updateProfile(data)
    userInfo.value = user
    role.value = (user as any).global_role || user.role
    return user
  }

  /** 从本地存储恢复用户信息（页面刷新时调用） */
  function restoreFromStorage(): void {
    const accessToken = getAccessToken()
    if (accessToken) {
      token.value = accessToken
    }
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
    // Actions
    login,
    logout,
    fetchProfile,
    updateProfile,
    restoreFromStorage,
  }
})
