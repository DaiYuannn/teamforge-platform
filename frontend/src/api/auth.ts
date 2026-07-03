import { get, post, patch, clearTokens } from './request'
import type { LoginParams, LoginResult, RefreshTokenResult, User, UpdateProfileParams } from '@/types'

/** 用户登录 */
export function login(data: LoginParams): Promise<LoginResult> {
  return post<LoginResult>('/auth/login/', data)
}

/** 刷新 Token */
export function refreshToken(refresh: string): Promise<RefreshTokenResult> {
  return post<RefreshTokenResult>('/auth/refresh/', { refresh })
}

/** 退出登录（后端无 logout 路由，仅在前端清除 Token） */
export function logout(): Promise<void> {
  clearTokens()
  return Promise.resolve()
}

/** 获取当前用户信息 */
export function getProfile(): Promise<User> {
  return get<User>('/users/me/')
}

/** 更新当前用户信息 */
export function updateProfile(data: UpdateProfileParams): Promise<User> {
  return patch<User>('/users/me/', data)
}
