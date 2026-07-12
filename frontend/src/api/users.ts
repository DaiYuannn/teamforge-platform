import { get, post, put, patch, del } from './request'
import type { User, UserFormData, PaginatedResponse, PaginationParams } from '@/types'

/** 用户查询参数 */
export interface UserQueryParams extends PaginationParams {
  global_role?: string
  is_active?: boolean
}

/** 获取用户列表 */
export function getUsers(params: UserQueryParams): Promise<PaginatedResponse<User>> {
  return get<PaginatedResponse<User>>('/users/', params)
}

/** 创建用户 */
export function createUser(data: UserFormData): Promise<User> {
  return post<User>('/users/', data)
}

/** 更新用户 */
export function updateUser(id: number, data: Partial<UserFormData>): Promise<User> {
  return patch<User>(`/users/${id}/`, data)
}

/** 删除用户 */
export function deleteUser(id: number): Promise<void> {
  return del<void>(`/users/${id}/`)
}

/** 获取用户详情 */
export function getUser(id: number): Promise<User> {
  return get<User>(`/users/${id}/`)
}

// ============================================
// 用户个人化偏好设置 API
// ============================================

/** 用户偏好设置数据结构 */
export interface UserPreferenceData {
  user_id?: number
  dashboard_layout: Record<string, unknown>
  theme_color: string
  default_landing: string
  sidebar_collapsed: boolean
  notification_sound: boolean
  items_per_page: number
}

/** 获取当前用户偏好设置 */
export function getUserPreference(): Promise<UserPreferenceData> {
  return get<UserPreferenceData>('/users/preference/')
}

/** 更新当前用户偏好设置 */
export function updateUserPreference(data: Partial<UserPreferenceData>): Promise<UserPreferenceData> {
  return put<UserPreferenceData>('/users/preference/', data)
}
