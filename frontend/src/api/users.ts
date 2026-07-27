import { get, post, put, patch, del } from './request'
import type { User, UserFormData, PaginatedResponse, PaginationParams, ThemeMode } from '@/types'

/** 用户查询参数 */
export interface UserQueryParams extends PaginationParams {
  global_role?: string
  is_active?: boolean
  membership_status?: string
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
  primary_color: string
  theme_color?: string
  theme_mode: ThemeMode
  schedule_start: string
  schedule_end: string
  default_landing: string
  sidebar_collapsed: boolean
  notification_sound: boolean
  language?: 'zh-CN' | 'en'
  items_per_page: number
  default_scope?: 'mine' | 'team'
  sidebar_order?: string[]
  favorite_routes?: string[]
  saved_filters?: Record<string, Record<string, unknown>>
  notification_preferences?: {
    categories?: Record<string, boolean>
    channels?: Record<string, boolean>
    quiet_hours?: { enabled?: boolean; start?: string; end?: string }
    digest?: 'instant' | 'daily' | 'weekly'
  }
}

/** 获取当前用户偏好设置 */
export function getUserPreference(): Promise<UserPreferenceData> {
  return get<UserPreferenceData>('/users/preference/')
}

/** 更新当前用户偏好设置 */
export function updateUserPreference(data: Partial<UserPreferenceData>): Promise<UserPreferenceData> {
  return put<UserPreferenceData>('/users/preference/', data)
}

export interface UserTransitionPayload {
  status: 'active' | 'on_leave' | 'exited' | 'external'
  reason?: string
  handover_to?: number
  handover_notes?: string
}

/** 变更成员状态，离队时保留其全部项目与贡献历史。 */
export function transitionUser(id: number, data: UserTransitionPayload): Promise<User> {
  return post<User>(`/users/${id}/transition/`, data)
}

export function getUserLifecycle(id: number): Promise<Array<Record<string, unknown>>> {
  return get<Array<Record<string, unknown>>>(`/users/${id}/lifecycle/`)
}
